# CDK Deploy
```bash
# Choose your region, and store it in this environment variable

export AWS_DEFAULT_REGION=<aws-region-here> # Example region: us-west-2
echo "export AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION >> ~/.bashrc"
```

AWS CDK pre-requisites:

- [Node.js](https://nodejs.org/en/download) >= 8.11.x

- Python >= 3.6

or

- Docker

Not using Docker:
```bash
CDK_VERSION=v1.0.0
npm install -g aws-cdk@${CDK_VERSION}
cdk --version
virtual env .env
source .env/bin/activate
pip install --upgrade -r requirements.txt
```
Using Docker:
```bash
CDK_VERSION=v1.0.0
function cdk { docker run -v $(pwd):/cdk -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -it adam9098/aws-cdk:${CDK_VERSION} $@; }
```

This installs the required libraries to run cdk. Choosing the Docker path takes a lot of the pain of having to install the libraries locally.


Build the cloudformation templates and view them in the `cdk.out` directory.
```bash
cdk synth 
```

Deploy the service
```bash
cdk deploy
```

That's it! Assuming you have the proper access defined for your IAM user, you should have deployed the service!

## Scale the tasks:
Open up in an editor of your choice `app.py`, and modify the `desired_service_count` variable to whatever number you wish.

```python
if __name__ == '__main__':
    _stack_name = 'fargate-demo'
    _vpc_name = '{}-base/BaseVPC'.format(_stack_name)
    # https://github.com/awslabs/aws-cdk/issues/3082
    _env = {'account': environ['CDK_DEFAULT_ACCOUNT'],'region': environ['CDK_DEFAULT_REGION']}
    
    app = core.App()
    
    BackendNodeECSService(app, 
        _stack_name + "-backend-nodejs", 
        base_stack_name=_stack_name,
        env=_env,
        desired_service_count=1, 
        vpc_name=_vpc_name
    )
    
    app.synth()
```

Validate your changes
```bash
cdk diff
```

If all looks good, ship it!
```bash
cdk deploy
```

## Cleanup:
```
cdk destroy
```


