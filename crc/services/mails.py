import os

from flask import render_template, render_template_string
from flask_mail import Message


# TODO: Extract common mailing code into its own function

def send_ramp_up_submission_email(sender, recipients, approver_1, approver_2=None):
    try:
        msg = Message('Research Ramp-up Plan Submitted',
              sender=sender,
              recipients=recipients)
        from crc import env, mail
        template = env.get_template('ramp_up_submission.txt')
        template_vars = {'approver_1': approver_1, 'approver_2': approver_2}
        msg.body = template.render(template_vars)
        template = env.get_template('ramp_up_submission.html')
        msg.html = template.render(template_vars)

        mail.send(msg)
    except Exception as e:
        return str(e)

def send_ramp_up_approval_request_email(sender, recipients, primary_investigator):
    try:
        msg = Message('Research Ramp-up Plan Approval Request',
              sender=sender,
              recipients=recipients)
        from crc import env, mail
        template = env.get_template('ramp_up_approval_request.txt')
        template_vars = {'primary_investigator': primary_investigator}
        msg.body = template.render(template_vars)
        template = env.get_template('ramp_up_approval_request.html')
        msg.html = template.render(template_vars)

        mail.send(msg)
    except Exception as e:
        return str(e)

def send_ramp_up_approval_request_first_review_email(sender, recipients, primary_investigator):
    try:
        msg = Message('Research Ramp-up Plan Approval Request',
              sender=sender,
              recipients=recipients)
        from crc import env, mail
        template = env.get_template('ramp_up_approval_request_first_review.txt')
        template_vars = {'primary_investigator': primary_investigator}
        msg.body = template.render(template_vars)
        template = env.get_template('ramp_up_approval_request_first_review.html')
        msg.html = template.render(template_vars)

        mail.send(msg)
    except Exception as e:
        return str(e)

def send_ramp_up_approved_email(sender, recipients, approver_1, approver_2=None):
    try:
        msg = Message('Research Ramp-up Plan Approved',
              sender=sender,
              recipients=recipients)

        from crc import env, mail
        template = env.get_template('ramp_up_approved.txt')
        template_vars = {'approver_1': approver_1, 'approver_2': approver_2}
        msg.body = template.render(template_vars)
        template = env.get_template('ramp_up_approved.html')
        msg.html = template.render(template_vars)

        mail.send(msg)
    except Exception as e:
        return str(e)

def send_ramp_up_denied_email(sender, recipients, approver):
    try:
        msg = Message('Research Ramp-up Plan Denied',
              sender=sender,
              recipients=recipients)

        from crc import env, mail
        template = env.get_template('ramp_up_denied.txt')
        template_vars = {'approver': approver}
        msg.body = template.render(template_vars)
        template = env.get_template('ramp_up_denied.html')
        msg.html = template.render(template_vars)

        mail.send(msg)
    except Exception as e:
        return str(e)

def send_ramp_up_denied_email_to_approver(sender, recipients, primary_investigator, approver_2):
    try:
        msg = Message('Research Ramp-up Plan Denied',
              sender=sender,
              recipients=recipients)

        from crc import env, mail
        template = env.get_template('ramp_up_denied_first_approver.txt')
        template_vars = {'primary_investigator': primary_investigator, 'approver_2': approver_2}
        msg.body = template.render(template_vars)
        template = env.get_template('ramp_up_denied_first_approver.html')
        msg.html = template.render(template_vars)

        mail.send(msg)
    except Exception as e:
        return str(e)
