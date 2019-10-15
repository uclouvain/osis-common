##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2019 Université catholique de Louvain (http://www.uclouvain.be)
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
##############################################################################
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, PageBreak, Table, TableStyle
from voluptuous import Schema, Any, Required, All, Url, Length, error as voluptuous_error

PAGE_SIZE = A4
MARGIN_SIZE = 15 * mm
COLS_WIDTH = [20*mm, 40*mm, 35*mm, 15*mm, 35*mm, 30*mm]
STUDENTS_PER_PAGE = 20
DATE_FORMAT = "%d/%m/%Y"


def print_notes(data):
    """
    Create a multi-page document
    :param data: all data context for PDF generation.
    :param tutor: If the user who's asking for the PDF is a Tutor, this var is assigned to the user linked to the tutor.
    """
    try:
        validate_data_structure(data)
        return build_response(data)
    except voluptuous_error.Invalid:
        return build_error_response()


def get_data_schema():
    return Schema({
        Required("institution"): str,
        Required("link_to_regulation"): Url(),
        Required("publication_date"): str,
        Required("justification_legend"): str,
        Required("tutor_global_id"): str,
        Required("learning_unit_years"): All([
            {
                 Required("session_number"): int,
                 Required("title"): str,
                 Required("academic_year"): str,
                 Required("acronym"): str,
                 Required("decimal_scores"): bool,
                 Required("programs"): [
                    {
                      Required("deliberation_date"): str,
                      Required("acronym"): str,
                      Required("address"): {},
                      Required("enrollments"): [{
                          Required("registration_id"): str,
                          Required("first_name", default=''): Any(None,str),
                          Required("last_name", default=''): Any(None, str),
                          Required("justification"): str,
                          Required("score"): str,
                          Required("deadline"): str
                      }]
                    }
                 ],
                 Required("scores_responsible"): {
                     Required("address"): {
                         Required("city"): str,
                         Required("postal_code"): str,
                         Required("location"): str
                     },
                     Required("first_name", default=''): Any(None, str),
                     Required("last_name", default=''): Any(None, str)
                 }
             }
        ], Length(min=1), extra=True)
    }, extra=True)


def validate_data_structure(data):
    s = get_data_schema()
    return s(data)


def build_error_response():
    return HttpResponse(status=500)


def build_response(data):
    luy = data.get('learning_unit_years')
    if luy and len(luy) == 1:
        filename = "session_%s_%s_%s.pdf" % (luy[0]['academic_year'][:4], luy[0]['session_number'], luy[0]['acronym'])
    else:
        filename = "%s.pdf" % _('Score sheet')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    pdf = build_pdf(data)
    response.write(pdf)
    return response


def build_pdf(data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer,
                            pagesize=PAGE_SIZE,
                            rightMargin=MARGIN_SIZE,
                            leftMargin=MARGIN_SIZE,
                            topMargin=85,
                            bottomMargin=18)
    content = _data_to_pdf_content(data)
    doc.build(content, onFirstPage=_write_header_and_footer, onLaterPages=_write_header_and_footer)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def _write_header_and_footer(canvas, doc):
    """
    Add the page number
    """
    styles = getSampleStyleSheet()
    # Save the state of our canvas so we can draw on it
    canvas.saveState()
    # Header
    _write_header(canvas, doc, styles)
    # Footer
    _write_footer(canvas, doc, styles)
    # Release the canvas
    canvas.restoreState()


def _write_header(canvas, doc, styles):
    a = Image(settings.LOGO_INSTITUTION_URL, width=60*mm, height=15*mm)
    p = Paragraph('''<para align=center>
                        <font size=16>%s</font>
                    </para>''' % (_('Score sheet')), styles["BodyText"])

    data_header = [[a, "", p], ]
    t_header = Table(data_header, [30*mm, 100*mm, 50*mm])
    t_header.setStyle(TableStyle([]))
    w, h = t_header.wrap(doc.width, doc.topMargin)
    t_header.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h)


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    return styles


def _data_to_pdf_content(json_data):
    styles = _build_styles()
    content = []
    for learn_unit_year in json_data['learning_unit_years']:
        for program in learn_unit_year['programs']:
            nb_students = len(program['enrollments'])
            for enrollments_by_pdf_page in chunks(program['enrollments'], STUDENTS_PER_PAGE):
                content.extend(_build_page_content(enrollments_by_pdf_page, learn_unit_year, nb_students, program, styles))
    return content


def _build_page_content(enrollments_by_pdf_page, learn_unit_year, nb_students, program, styles):
    page_content = []
    # 1. Write addresses & programs info
    # We add first a blank line
    page_content.append(Paragraph('''<para spaceb=20>&nbsp;</para>''', ParagraphStyle('normal')))
    page_content.append(_build_header_addresses_block(learn_unit_year, program, styles))
    page_content.extend(_build_program_block_content(learn_unit_year, nb_students, program, styles))
    # 2. Adding the complete table of examEnrollments to the PDF sheet
    page_content.append(_build_exam_enrollments_table(enrollments_by_pdf_page, styles))
    # 3. Write Legend
    page_content.extend(_build_signature_content())
    page_content.append(_build_legend_block(learn_unit_year['decimal_scores']))
    # 4. New Page
    page_content.append(PageBreak())
    return page_content


def _build_exam_enrollments_table(enrollments_by_pdf_page, styles):
    students_table = _students_table_header()
    for enrollment in enrollments_by_pdf_page:
        student_last_name = enrollment["last_name"] if enrollment["last_name"] else ""
        student_first_name = enrollment["first_name"] if enrollment["first_name"] else ""

        # 1. Append the examEnrollment to the table 'students_table'
        students_table.append([enrollment["registration_id"],
                               Paragraph(student_last_name, styles['Normal']),
                               Paragraph(student_first_name, styles['Normal']),
                               enrollment["score"],
                               Paragraph(_(enrollment["justification"]), styles['Normal']),
                               enrollment["deadline"]])

    table = Table(students_table, COLS_WIDTH, repeatRows=1)
    table.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey)]))

    for idx, enrollment in enumerate(enrollments_by_pdf_page,1):
        if enrollment.get("enrollment_state_color"):
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, idx), (5, idx), enrollment["enrollment_state_color"])]))

    return table


def _students_table_header():
    data = [['''%s''' % _('Reg. No.'),
             '''%s''' % _('Lastname'),
             '''%s''' % _('Firstname'),
             '''%s''' % _('Score'),
             '''%s''' % _('Justification (A,T)'),
             '''%s''' % _('Submit data')
             ]]
    return data


def _build_header_addresses_block(learning_unit_year, program, styles):
    header_address_structure = [[_build_header_scores_responsible_address(learning_unit_year, styles),
                                 _build_header_secretariat_address_block(program, styles)]]
    table_header = Table(header_address_structure, colWidths='*')
    table_header.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    return table_header


def _build_header_scores_responsible_address(learning_unit_year, styles):
    scores_responsible = learning_unit_year["scores_responsible"]
    address = scores_responsible['address']
    return [[Paragraph(_get_scores_responsible_title_text(), styles["Normal"])],
            [Paragraph(_get_scores_responsible_text(scores_responsible), styles["Normal"])],
            [Paragraph(_get_scores_responsible_location_text(address), styles["Normal"])],
            [Paragraph(_get_scores_responsible_city_text(address), styles["Normal"])]]


def _get_scores_responsible_city_text(address):
    return '{} {}'.format(address['postal_code'] or '', address['city'] or '')


def _get_scores_responsible_location_text(address):
    return '{}'.format(address['location'] or '')


def _get_scores_responsible_title_text():
    return '<b>{} :</b>'.format(_('Scores responsible'))


def _get_scores_responsible_text(scores_responsible):
    if scores_responsible:
        last_name = scores_responsible["last_name"] if scores_responsible['last_name'] else ""
        first_name = scores_responsible["first_name"] if scores_responsible['first_name'] else ""
        return '{} {}'.format(last_name, first_name)
    return '{}'.format(_('None'))


def _build_header_secretariat_address_block(program, styles):
    secretariat_address = program['address']
    data_structure = [[Paragraph(_('Université catholique de Louvain'), styles["Normal"])],
                      [Paragraph(_get_recipient_text(secretariat_address), styles["Normal"])],
                      [Paragraph(_get_location_text(secretariat_address), styles["Normal"])],
                      [Paragraph(_get_postal_code_and_city_text(secretariat_address), styles["Normal"])],
                      [Paragraph(_get_phone_and_fax_text(secretariat_address), styles["Normal"])]]
    if secretariat_address.get('email'):
        data_structure.append([Paragraph(_get_email_text(secretariat_address), styles["Normal"])])
    return data_structure


def _get_email_text(secretariat_address):
    return '{0} : {1}'.format(_('Email'), secretariat_address.get('email'))


def _get_location_text(secretariat_address):
    return '{}'.format(secretariat_address.get('location') or '')


def _get_recipient_text(secretariat_address):
    return '{}'.format(secretariat_address.get('recipient') or '')


def _get_postal_code_and_city_text(secretariat_address):
    return '{} {}'.format(secretariat_address.get('postal_code'), secretariat_address.get('city'))


def _get_phone_and_fax_text(secretariat_address):
    phone_fax_text = ""
    phone = secretariat_address.get('phone')
    fax = secretariat_address.get('fax')
    if phone:
        phone_fax_text = "{} : {}".format(_('Phone'), phone)
        if fax:
            phone_fax_text += " - "
            phone_fax_text += _get_fax_text(fax)
    elif fax:
        phone_fax_text += _get_fax_text(fax)
    return phone_fax_text


def _get_fax_text(fax):
    return "{} : {}".format(_('Fax'), fax)


def _build_program_block_content(learning_unit_year, nb_students, program, styles):
    text_left_style = ParagraphStyle('structure_header')
    text_left_style.alignment = TA_LEFT
    text_left_style.fontSize = 10
    return [
        Paragraph(_get_deliberation_date_text(program), styles["Normal"]),
        Paragraph(_get_academic_year_text(learning_unit_year), text_left_style),
        Paragraph(_get_learning_unit_year_text(learning_unit_year), styles["Normal"]),
        Paragraph(_get_program_text(nb_students, program), styles["Normal"]),
        Paragraph('''<para spaceb=2> &nbsp; </para> ''', ParagraphStyle('normal'))
    ]


def _get_program_text(nb_students, program):
    return '''<b>{} : {} </b>({} {})'''.format(_('Program'),
                                               program['acronym'],
                                               nb_students,
                                               _('students') if nb_students > 1 else _('student'))


def _get_learning_unit_year_text(learning_unit_year):
    return "<strong>{} : {}</strong>".format(learning_unit_year['acronym'], learning_unit_year['title'])


def _get_deliberation_date_text(program):
    return '%s : %s' % (_('Deliberation date'), program['deliberation_date'] or '')


def _get_academic_year_text(learning_unit_year):
    return '{} : {}  - Session : {}'.format(_('Academic year'),
                                            learning_unit_year['academic_year'],
                                            learning_unit_year['session_number'])


def _build_signature_content():
    return [
        Paragraph('''<para spaceb=5> &nbsp; </para>''', ParagraphStyle('normal')),
        _build_signature_paragraph(),
        Paragraph(''' <para spaceb=2> &nbsp; </para> ''', ParagraphStyle('normal'))
    ]


def _build_signature_paragraph():
    p_signature = ParagraphStyle('info')
    p_signature.fontSize = 10
    paragraph_signature = Paragraph('''
                    <font size=10>%s ...................................... , </font>
                    <font size=10>%s ..../..../.......... &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</font>
                    <font size=10>%s</font>
                   ''' % (_('Done at'), _('the'), _('Signature')), p_signature)
    return paragraph_signature


def _build_legend_block(decimal_scores):
    creation_date = timezone.now()
    creation_date = creation_date.strftime(DATE_FORMAT)

    legend_text = str(_('Justification legend: A=Absent, T=Cheating'))
    legend_text += "<br/>%s" % (str(_('Score legend: {score} (0=Score of presence)').format(score="0 - 20")))
    if decimal_scores:
        legend_text += "<br/><font color=red>%s</font>" % _('Decimals authorized for this learning unit')
    else:
        legend_text += "<br/><font color=red>%s</font>" % _('Unauthorized decimal for this learning unit')

    legend_text += "<br/><span backColor=#dff0d8>&nbsp; %s &nbsp;</span>" % _('Enrolled lately')
    legend_text += " - <span backColor=#f2dede>&nbsp; %s &nbsp;</span>" % _('Unsubscribed lately')
    legend_text += '''<br/> %s : <a href="%s"><font color=blue><u>%s</u></font></a>''' \
                   % (_("In accordance to regulation's rules 104, 109 and 111. Complete rules avalaible here"), 
                      _("https://uclouvain.be/fr/decouvrir/rgee.html"),
                      _("https://uclouvain.be/fr/decouvrir/rgee.html"))

    legend_text += "<br/><font color=red>%s</font>" % str(
        _(
            'The data presented on this document correspond to the state of the system dated %(creation_date)s and are '
            'likely to evolve'
        )%
            {
                'creation_date': creation_date,
            }

    )

    return Paragraph('''<para> %s </para>''' % legend_text, _build_legend_block_style())


def _build_legend_block_style():
    style = ParagraphStyle('legend')
    style.textColor = 'grey'
    style.borderColor = 'grey'
    style.borderWidth = 1
    style.alignment = TA_CENTER
    style.fontSize = 8
    style.borderPadding = 5
    return style


def _write_footer(canvas, doc, styles):
    creation_date = timezone.now()
    creation_date = creation_date.strftime(DATE_FORMAT)
    pageinfo = "%s : %s" % (_('Creation date'), creation_date)
    footer = Paragraph(''' <para align=right>Page %d - %s </para>''' % (doc.page, pageinfo), styles['Normal'])
    w, h = footer.wrap(doc.width, doc.bottomMargin)
    footer.drawOn(canvas, doc.leftMargin, h)
