from flask_mail import Message
from jinja2 import Environment, FileSystemLoader

from crc import app, mail
from crc.services.email_service import EmailService

# Jinja environment definition, used to render mail templates
template_dir = app.root_path + '/static/templates/mails'
env = Environment(loader=FileSystemLoader(template_dir))


def send_test_email(sender, recipients):
    try:
        msg = Message('Research Ramp-up Plan test',
                      sender=sender,
                      recipients=recipients,
                      bcc=['rrt_emails@googlegroups.com'])
        template = env.get_template('ramp_up_approval_request_first_review.txt')
        template_vars = {'primary_investigator': "test"}
        msg.body = template.render(template_vars)
        template = env.get_template('ramp_up_approval_request_first_review.html')
        msg.html = template.render(template_vars)
        mail.send(msg)
    except Exception as e:
        return str(e)


def send_mail(subject, sender, recipients, content, content_html, study_id=None):
    EmailService.add_email(subject=subject, sender=sender, recipients=recipients,
                           content=content, content_html=content_html, study_id=study_id)


def send_ramp_up_submission_email(sender, recipients, approver_1, approver_2=None):
    subject = 'Research Ramp-up Plan Submitted'

    template = env.get_template('ramp_up_submission.txt')
    template_vars = {'approver_1': approver_1, 'approver_2': approver_2}
    content = template.render(template_vars)
    template = env.get_template('ramp_up_submission.html')
    content_html = template.render(template_vars)

    send_mail(subject, sender, recipients, content, content_html)


def send_ramp_up_approval_request_email(sender, recipients, primary_investigator):
    subject = 'Research Ramp-up Plan Approval Request'

    template = env.get_template('ramp_up_approval_request.txt')
    template_vars = {'primary_investigator': primary_investigator}
    content = template.render(template_vars)
    template = env.get_template('ramp_up_approval_request.html')
    content_html = template.render(template_vars)

    send_mail(subject, sender, recipients, content, content_html)


def send_ramp_up_approval_request_first_review_email(sender, recipients, primary_investigator):
    subject = 'Research Ramp-up Plan Approval Request'

    template = env.get_template('ramp_up_approval_request_first_review.txt')
    template_vars = {'primary_investigator': primary_investigator}
    content = template.render(template_vars)
    template = env.get_template('ramp_up_approval_request_first_review.html')
    content_html = template.render(template_vars)

    send_mail(subject, sender, recipients, content, content_html)


def send_ramp_up_approved_email(sender, recipients, approver_1, approver_2=None):
    subject = 'Research Ramp-up Plan Approved'

    template = env.get_template('ramp_up_approved.txt')
    template_vars = {'approver_1': approver_1, 'approver_2': approver_2}
    content = template.render(template_vars)
    template = env.get_template('ramp_up_approved.html')
    content_html = template.render(template_vars)

    send_mail(subject, sender, recipients, content, content_html)


def send_ramp_up_denied_email(sender, recipients, approver):
    subject = 'Research Ramp-up Plan Denied'

    template = env.get_template('ramp_up_denied.txt')
    template_vars = {'approver': approver}
    content = template.render(template_vars)
    template = env.get_template('ramp_up_denied.html')
    content_html = template.render(template_vars)

    send_mail(subject, sender, recipients, content, content_html)


def send_ramp_up_denied_email_to_approver(sender, recipients, primary_investigator, approver_2):
    subject = 'Research Ramp-up Plan Denied'

    template = env.get_template('ramp_up_denied_first_approver.txt')
    template_vars = {'primary_investigator': primary_investigator, 'approver_2': approver_2}
    content = template.render(template_vars)
    template = env.get_template('ramp_up_denied_first_approver.html')
    content_html = template.render(template_vars)

    send_mail(subject, sender, recipients, content, content_html)
