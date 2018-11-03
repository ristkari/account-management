import sys
import time
import click
import boto3
import botocore
from botocore.exceptions import ClientError

from halo import Halo
import colored
from colored import stylize

import inquirer

cloudformation_templates = ['IAM', 'CONFIG', 'VPC']


@click.command()
@click.option("--new_account_name", help="Name of the AWS account being created.")
@click.option("--profile_name", help="AWS profile for master account.")
@click.option("--admin_role_name", help="Admin role being created")
@click.option("--admin_email", help="Email associated with root-user.")
@click.option("--region", help="Which region to use", type=click.Choice(['us-east-1', 'us-east-2', 'us-west-1',
                                                                         'us-west-2', 'eu-west-1', 'eu-west-2',
                                                                         'eu-west-3', 'ca-central-1', 'ap-northeast-1',
                                                                         'ap-northeast-2', 'ap-southeast-1',
                                                                         'ap-southeast-2', 'sa-east-1']))
@click.option("--billing_access", help="Is IAM users allowed to access billing data.",
              type=click.Choice(['ALLOW', 'DENY']))
def create_account(new_account_name, profile_name, admin_role_name, admin_email, billing_access, region):

    data = {}

    if new_account_name is None:
        account_name = [
            inquirer.Text('account_name',
                          message="Enter new account name: ")]
        data['account_name'] = inquirer.prompt(account_name).get('account_name')
    else:
        data['account_name'] = new_account_name

    if profile_name is None:
        master_account_profile = [
            inquirer.Text('master_profile',
                          message="Select correct master-account?")]
        data['master_profile'] = inquirer.prompt(master_account_profile).get('master_profile')
    else:
        data['master_profile'] = profile_name

    if admin_role_name is None:
        role_name = [
            inquirer.Text('admin_role_name',
                          message="Enter your admin role-name to be created: ")]
        data['role_name'] = inquirer.prompt(role_name).get('admin_role_name')
    else:
        data['role_name'] = admin_role_name

    if admin_email is None:
        admin_email_address = [
            inquirer.Text('admin_email',
                          message="Enter your root accounts email: ")]
        data['admin_email'] = inquirer.prompt(admin_email_address).get('admin_email')
    else:
        data['admin_email'] = admin_email

    if billing_access is None:
        billing_access_allowed = [
            inquirer.List('billing_allowed',
                          message="IAM billing access allowed?",
                          choices=['ALLOW', 'DENY'],
                          carousel=True
                          ),
        ]
        data['allow_billing'] = inquirer.prompt(billing_access_allowed).get('billing_allowed')
    else:
        data['allow_billing'] = billing_access

    if region is None:
        region_selection = [
            inquirer.List('region',
                          message="Which region to use?",
                          choices=['us-east-1', 'us-east-2', 'us-west-1',
                                   'us-west-2', 'eu-west-1', 'eu-west-2',
                                   'eu-west-3', 'ca-central-1', 'ap-northeast-1',
                                   'ap-northeast-2', 'ap-southeast-1',
                                   'ap-southeast-2', 'sa-east-1'],
                          carousel=True
                          ),
        ]
        data['region'] = inquirer.prompt(region_selection).get('region')
    else:
        data['region'] = region

    session = boto3.session.Session(profile_name=data.get('master_profile'))
    client = session.client('organizations')
    spinner = Halo(text='Starting account creation', spinner='dots', color='magenta')
    spinner.start()
    try:
        create_account_response = client.create_account(Email=data.get('admin_email'),
                                                        AccountName=data.get('account_name'),
                                                        RoleName=data.get('role_name'),
                                                        IamUserAccessToBilling=data.get('allow_billing'))
        spinner.succeed('Account creation initiated')
    except botocore.exceptions.ClientError as e:
        spinner.fail('Call failed when trying to initiate account creation')
        print(e)
        sys.exit(1)

    spinner = Halo(text='Waiting for completion', spinner='dots', color='magenta')
    spinner.start()
    account_id = None
    create_account_status_response = None
    account_status = 'IN_PROGRESS'
    while account_status == 'IN_PROGRESS':
        time.sleep(3)
        create_account_status_response = client.describe_create_account_status(
            CreateAccountRequestId=create_account_response.get('CreateAccountStatus').get('Id'))
        account_status = create_account_status_response.get('CreateAccountStatus').get('State')
        # account_status = 'SUCCEEDED'
        time.sleep(3)
    if account_status == 'SUCCEEDED':
        spinner.succeed('Account created successfully')
        account_id = create_account_status_response.get('CreateAccountStatus').get('AccountId')
        # account_id = "253208383587"
    elif account_status == 'FAILED':
        spinner.fail('Account creation failed')
        print(stylize("Account creation failed: " + create_account_status_response.get('CreateAccountStatus').get(
            'FailureReason')), colored.fg("red"))
        sys.exit(1)

    cf_template = read_template('base.yaml')
    # account_id = "253208383587"
    assumed_role = assume_role(account_id,
                               data.get('role_name'),
                               data.get('master_profile'),
                               data.get('region'))
    deploy_cloudformation(assumed_role, cf_template, 'Base-stack', data.get('region'),
                          {'admin_username': 'abcdefghijklmnopqrstyvwxyz',
                           'admin_password': '12345677890'})

    return {"account_id": account_id}


def assume_role(account_id, account_role, profile_name, region_name):
    spinner = Halo(text='Assuming role', spinner='dots', color='magenta')
    spinner.start()
    session = boto3.session.Session(profile_name=profile_name)
    sts_client = session.client('sts', region_name=region_name)
    role_arn = 'arn:aws:iam::' + account_id + ':role/' + account_role
    assumed_role_object = None
    assuming_role = True
    while assuming_role is True:
        try:
            assuming_role = False
            assumed_role_object = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName="AccountAutomation"
            )
        except botocore.exceptions.ClientError as e:
            assuming_role = True
            spinner.fail("Assume role failed.")
            print(e)
            print("Retrying...")
            time.sleep(10)
    spinner.succeed("Assumed role")
    return assumed_role_object.get('Credentials')


def deploy_cloudformation(credentials, template_source, stack_name, stack_region, parameters):
    datestamp = time.strftime("%d/%m/%Y")
    client = boto3.client('cloudformation',
                          aws_access_key_id=credentials['AccessKeyId'],
                          aws_secret_access_key=credentials['SecretAccessKey'],
                          aws_session_token=credentials['SessionToken'],
                          region_name=stack_region)

    creating_stack = True
    while creating_stack is True:
        try:
            creating_stack = False
            create_stack_response = client.create_stack(
                StackName=stack_name,
                TemplateBody=template_source,
                Parameters=[
                    {
                        'ParameterKey': 'AdminUsername',
                        'ParameterValue': parameters.get('admin_username')
                    },
                    {
                        'ParameterKey': 'AdminPassword',
                        'ParameterValue': parameters.get('admin_password')
                    }
                ],
                NotificationARNs=[],
                Capabilities=[
                    'CAPABILITY_NAMED_IAM',
                ],
                OnFailure='ROLLBACK',
                Tags=[
                    {
                        'Key': 'ManagedResource',
                        'Value': 'True'
                    },
                    {
                        'Key': 'DeployDate',
                        'Value': datestamp
                    }
                ]
            )
        except botocore.exceptions.ClientError as e:
            creating_stack = True
            print(e)
            time.sleep(10)

    stack_building = True
    spinner = Halo(text='Stack: ' + stack_name + ' creation in process...', spinner='dots', color='magenta')
    spinner.start()
    while stack_building is True:
        event_list = client.describe_stack_events(StackName=stack_name).get("StackEvents")
        stack_event = event_list[0]

        if (stack_event.get('ResourceType') == 'AWS::CloudFormation::Stack' and
                stack_event.get('ResourceStatus') == 'CREATE_COMPLETE'):
            stack_building = False
            spinner.succeed("Stack creation complete.")
        elif (stack_event.get('ResourceType') == 'AWS::CloudFormation::Stack' and
              stack_event.get('ResourceStatus') == 'ROLLBACK_COMPLETE'):
            spinner.fail("Stack creation failed.")
            sys.exit(1)
        else:
            time.sleep(10)
    time.sleep(3)
    stack = client.describe_stacks(StackName=stack_name)
    return stack


def read_template(template_file):
    spinner = Halo(text='Reading template', spinner='dots', color='magenta')
    spinner.start()
    f = open(template_file, "r")
    cf_template = f.read()
    spinner.succeed("Template loaded.")
    return cf_template


if __name__ == '__main__':
    acc_id = create_account()

    for template in cloudformation_templates:
        print(template + '.yaml')
