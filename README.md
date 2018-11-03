# Account-management

Python scripting for automatic AWS account creation. Basics proudly copied from AWS examples.

account-management.py is python3 script which automatically tries to create AWS accounts.


```
❯ python3 account-management.py --help                                                                                                                   account-management-F0vXr1my
Usage: account-management.py [OPTIONS]

Options:
  --new_account_name TEXT         Name of the AWS account being created.
  --profile_name TEXT             AWS profile for master account.
  --admin_role_name TEXT          Admin role being created
  --admin_email TEXT              Email associated with root-user.
  --region [us-east-1|us-east-2|us-west-1|us-west-2|eu-west-1|eu-west-2|eu-west-3|ca-central-1|ap-northeast-1|ap-northeast-2|ap-southeast-1|ap-southeast-2|sa-east-1]
                                  Which region to use
  --billing_access [ALLOW|DENY]   Is IAM users allowed to access billing data.
  --help                          Show this message and exit.
``` 

Options can be passed as parameters or if not provided the script will prompt for infoprmation:

```
❯ python3 account-management.py                                                                                                                          account-management-F0vXr1my
[?] Enter new account name: : example-account
[?] Select correct master-account?: example-master-account-profile
[?] Enter your admin role-name to be created: : example-admin-role-to-be-created
[?] Enter your root accounts email: : example@domain.com
[?] IAM billing access allowed?: ALLOW
 > ALLOW
   DENY

[?] Which region to use?: eu-west-1
   us-east-1
   us-east-2
   us-west-1
   us-west-2
 > eu-west-1
   eu-west-2
   eu-west-3
   ca-central-1
   ap-northeast-1
   ap-northeast-2
   ap-southeast-1
   ap-southeast-2
   sa-east-1
```