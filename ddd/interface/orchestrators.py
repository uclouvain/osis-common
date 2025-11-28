# ##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2025 Université catholique de Louvain (http://www.uclouvain.be)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
# ##############################################################################
import datetime
import uuid
from abc import ABC
from abc import abstractmethod
from datetime import datetime
from enum import Enum
from typing import Protocol, List

from django.db import models
from django.db import transaction, DatabaseError


class StepState(str, Enum):
    PENDING = "PENDING"
    OK = "OK"
    ERROR = "ERROR"


class Workflow(Protocol):
    """
    Représente un état de workflow pouvant être manipulé par un orchestrateur.
    (Ex: modèle Django / SimpleNamespace)
    """
    uuid: uuid.UUID
    current_step: str
    step_state: StepState
    step_execution_count: int
    histories: List[dict]
    last_execution: datetime


class BaseStep(ABC):
    """
    Représente une étape unique du workflow (exécutable, identifiable par un nom).
    La classe contient la logique métier d'une étape.
    """
    name: str

    @classmethod
    @abstractmethod
    def do_run(cls, workflow: Workflow, **kwargs):
        pass

    @classmethod
    def compensate(cls, workflow: Workflow, failed_step_name: str, **kwargs):
        """
        Exécuté en cas d’échec du workflow après cette étape. À overrider si cette étape a des effets à annuler.
        :param failed_step_name: Nom de l’étape qui a échoué
        """
        pass


class TransactionStep(BaseStep):
    """
    Représente une étape unique du workflow (exécutable, identifiable par un nom et ayant le sid d'un savepoint)
    Sans dépendances externes synchrones (envoi de mail, ...)
    Par défaut, le compensate rollback la transaction englobée par le savepoint
    """
    savepoint_id: str

    @classmethod
    def compensate(cls, workflow: Workflow, failed_step_name: str, **kwargs):
        if cls.savepoint_id:
            transaction.savepoint_rollback(cls.savepoint_id)


class BaseOrchestrator(ABC):
    """
    Contient la logique d’enchaînement des étapes
    """
    _steps: list[BaseStep]

    @abstractmethod
    def run(self, workflow_uuid: uuid.UUID) -> None:
       pass


class InMemoryOrchestratorMixin(ABC):
    """
    Mixin pour exécuter un workflow en mémoire (sans base de données).
    """
    def run(self, workflow: Workflow) -> None:
        current_step_idx = next(
            i for i, step in enumerate(self._steps)
            if step.name == workflow.current_step
        )

        executed_steps = []
        for step in self._steps[current_step_idx:]:
            workflow.current_step = step.name
            workflow.step_execution_count += 1
            try:
                step.do_run(workflow=workflow)
                if workflow.step_state == StepState.PENDING:
                    break
                workflow.step_execution_count = 0
                executed_steps.append(step)
            except Exception as e:
                workflow.step_state = StepState.ERROR
                workflow.histories.append({
                    'name': step.name,
                    'date': datetime.now().isoformat(),
                    'state': workflow.step_state,
                    'description': f"{repr(e)}"
                })

                for prev_step in reversed(executed_steps):
                    try:
                        prev_step.compensate(workflow=workflow, failed_step_name=step.name)
                    except Exception as rollback_error:
                        workflow.histories.append({
                            'name': prev_step.name,
                            'date': datetime.now().isoformat(),
                            'state': StepState.ERROR,
                            'description': f"[Compensation Error] {repr(rollback_error)}"
                        })
                break


class OrchestratorModel(models.Model):
    """
    Modèle abstrait à hériter pour créer un modèle de persistance d'un orchestrateur.
    """
    STEP_STATE_CHOICES = [
        (StepState.PENDING.name, "En attente"),
        (StepState.ERROR.name, "En erreur"),
        (StepState.OK.name, "Ok"),
    ]
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_step = models.CharField(max_length=255)
    step_state = models.CharField(max_length=50, choices=STEP_STATE_CHOICES, default=StepState.PENDING.name)
    step_execution_count = models.IntegerField(default=0)
    last_execution = models.DateTimeField(auto_now=True)
    histories = models.JSONField(default=list)
    context_data = models.JSONField(default=dict, help_text="Données de contexte partagées entre les étapes de la saga")

    class Meta:
        abstract = True


class PersistedOrchestratorMixin(ABC):
    """
    Mixin pour orchestrateur avec persistance Django.
    """
    max_retries_workflow_in_error = 3
    model_class: type[OrchestratorModel] = None

    def load_workflow_instance(self, workflow_uuid: uuid.UUID):
        try:
            return self.model_class.objects.select_for_update(nowait=True).get(uuid=workflow_uuid)
        except DatabaseError:
            raise WorkflowEnCoursDeTraitementException

    def run(self, workflow_uuid: uuid.UUID) -> None:
        if self.model_class is None:
            raise Exception("model_class doit être défini")

        with transaction.atomic():
            workflow = self.load_workflow_instance(workflow_uuid)

            if workflow.step_execution_count >= self.max_retries_workflow_in_error:
                raise WorkflowEnErreurMaxRetryReachedException

            workflow.last_execution = datetime.now()
            current_step_idx = next(
                i for i, step in enumerate(self._steps) if step.name == workflow.current_step
            )
            executed_steps = []
            for step in self._steps[current_step_idx:]:
                workflow.current_step = step.name
                workflow.step_execution_count += 1
                try:
                    step.do_run(workflow=workflow)
                    if workflow.step_state == StepState.PENDING.name:
                        break
                    workflow.step_execution_count = 0
                    executed_steps.append(step)
                except Exception as e:
                    workflow.step_state = StepState.ERROR.name
                    workflow.histories.append({
                        'name': step.name,
                        'date': datetime.now().isoformat(),
                        'state':  StepState.ERROR.name,
                        'description': f"{getattr(e, 'message', repr(e))}"
                    })

                    for prev_step in reversed(executed_steps):
                        try:
                            prev_step.compensate(workflow=workflow, failed_step_name=step.name)
                        except Exception as rollback_error:
                            workflow.histories.append({
                                'name': prev_step.name,
                                'date': datetime.now().isoformat(),
                                'state':  StepState.ERROR,
                                'description': f"[Compensation Error] {repr(rollback_error)}"
                            })
                    break
        workflow.save()

    @abstractmethod
    def get_or_initialize(self, *args, **kwargs) -> uuid.UUID:
        pass



class WorkflowEnCoursDeTraitementException(Exception):
    pass


class WorkflowEnErreurMaxRetryReachedException(Exception):
    pass