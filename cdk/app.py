#!/usr/bin/env python3

# CDK v1.0.0
from aws_cdk import (
    aws_ec2,
    aws_ecs,
    aws_ecs_patterns,
    aws_elasticloadbalancingv2,
    aws_logs,
    aws_servicediscovery,
    core,
)

from os import environ


# This is an example of building our own construct. Rather than define these resources within the Stack, we can use this construct for isolation.
# Another neat thing here is that this could very easily be reused by pulling this code down from a centralized repo and importing it.
class BaseStackDependencies(core.Construct):
    
    def __init__(self, scope: core.Construct, id: str, vpc_name, base_stack_name, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.vpc_name = vpc_name
        self.base_stack_name = base_stack_name + "-base"
    
        # Importing the VPC as this is an object we will reference for the ECS cluster and others
        self.vpc = aws_ec2.Vpc.from_lookup(
            self, "VpcId",
            vpc_name=self.vpc_name
        )
        
        # Importing the ecs cluster as an object that will be referenced when creating our service
        self.ecs_cluster = aws_ecs.Cluster.from_cluster_attributes(
            self, "ECSCluster",
            cluster_name=core.Fn.import_value(self.base_stack_name + '-ecs-cluster-name'),
            vpc=self.vpc,
            default_cloud_map_namespace=aws_servicediscovery.PrivateDnsNamespace.from_private_dns_namespace_attributes(
                self, "ServiceDiscoveryZone",
                namespace_arn=core.Fn.import_value(self.base_stack_name + '-service-discovery-name'),
                namespace_id=core.Fn.import_value(self.base_stack_name + '-service-discovery-id'),
                namespace_name=core.Fn.import_value(self.base_stack_name + '-service-discovery-arn')
            ),
            security_groups=[ 
                aws_ec2.SecurityGroup.from_security_group_id(
                    self, "ECSClusterSecGrp",
                    core.Fn.import_value(self.base_stack_name + '-ecs-cluster-sec-grp')
                )
            ]
        )
        
        # Importing centrally managed security group for backend services
        self.services_3000_sec_group = aws_ec2.SecurityGroup.from_security_group_id(
            self, "SharedServicesSecGrp",
            security_group_id=core.Fn.import_value(self.base_stack_name + '-backend-services-security-group-id')
        )


class BackendNodeECSService(core.Stack):

    def __init__(self, scope: core.Stack, id: str, desired_service_count, vpc_name, base_stack_name, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.desired_service_count = desired_service_count
        self.vpc_name = vpc_name
        self.base_stack_name = base_stack_name
        
        # Loads all dependencies from centralized base stack (VPC, ECS Cluster, etc)
        self.base_stack = BaseStackDependencies(self, "Dependencies", vpc_name=self.vpc_name, base_stack_name=self.base_stack_name)

        # Creating the task definition and defining the per task specifications
        self.task_definition = aws_ecs.FargateTaskDefinition(
            self, "BackendNodeServiceTaskDef",
            cpu=256,
            memory_limit_mib=512,
        )

        # Container definition within the task definition
        self.task_definition.add_container(
            "BackendNodeServiceContainer",
            image=aws_ecs.ContainerImage.from_registry("brentley/ecsdemo-nodejs"),
            logging=aws_ecs.AwsLogDriver(stream_prefix="ecsdemo-nodejs", log_retention=aws_logs.RetentionDays.THREE_DAYS),
        )

        # Service definition to setup task to run indefinitely
        self.fargate_service = aws_ecs.FargateService(
            self, "BackendNodeFargateService",
            service_name="ecsdemo-nodejs",
            task_definition=self.task_definition,
            cluster=self.base_stack.ecs_cluster,
            max_healthy_percent=100,
            min_healthy_percent=0,
            vpc_subnets=self.base_stack.vpc.private_subnets,
            desired_count=self.desired_service_count,
            cloud_map_options={
                "name": "ecsdemo-nodejs"
            },
            security_group=self.base_stack.services_3000_sec_group,
        )


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
