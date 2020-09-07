#!/usr/bin/env python3

# cdk: 1.25.0
from aws_cdk import (
    aws_ec2,
    aws_ecs,
    aws_ecs_patterns,
    aws_iam,
    aws_servicediscovery,
    core,
)

from os import getenv


# Creating a construct that will populate the required objects created in the platform repo such as vpc, ecs cluster, and service discovery namespace
class BasePlatform(core.Construct):

    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.environment_name = 'ecsworkshop'

        # The base platform stack is where the VPC was created, so all we need is the name to do a lookup and import it into this stack for use
        self.vpc = aws_ec2.Vpc.from_lookup(
            self, "VPC",
            vpc_name='{}-base/BaseVPC'.format(self.environment_name)
        )

        self.sd_namespace = aws_servicediscovery.PrivateDnsNamespace.from_private_dns_namespace_attributes(
            self, "SDNamespace",
            namespace_name=core.Fn.import_value('NSNAME'),
            namespace_arn=core.Fn.import_value('NSARN'),
            namespace_id=core.Fn.import_value('NSID')
        )

        self.ecs_cluster = aws_ecs.Cluster.from_cluster_attributes(
            self, "ECSCluster",
            cluster_name=core.Fn.import_value('ECSClusterName'),
            security_groups=[],
            vpc=self.vpc,
            default_cloud_map_namespace=self.sd_namespace
        )

        self.services_sec_grp = aws_ec2.SecurityGroup.from_security_group_id(
            self, "ServicesSecGrp",
            security_group_id=core.Fn.import_value('ServicesSecGrp')
        )

        
class NodejsService(core.Stack):
    
    def nodejsTempEc2StressTool(self):
        
        # AMI 
        amzn_linux = aws_ec2.MachineImage.latest_amazon_linux(
            generation=aws_ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=aws_ec2.AmazonLinuxEdition.STANDARD,
            virtualization=aws_ec2.AmazonLinuxVirt.HVM,
            storage=aws_ec2.AmazonLinuxStorage.GENERAL_PURPOSE
            )

        # Instance Role and SSM Managed Policy
        role = aws_iam.Role(self, "InstanceSSM", assumed_by=aws_iam.ServicePrincipal("ec2.amazonaws.com"))

        role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2RoleforSSM"))
        

        #reading user data to install siege
        with open("stresstool_user_data.sh") as f:
            user_data = f.read()
    
        # Instance
        instance = aws_ec2.Instance(self, "Instance",
            instance_name="{}-nodejs-stresstool".format(environment),
            instance_type=aws_ec2.InstanceType("t3.medium"),
            machine_image=amzn_linux,
            vpc = self.base_platform.vpc,
            role = role,
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE),
            user_data=aws_ec2.UserData.custom(user_data),
            security_group=self.base_platform.services_sec_grp,
            )
        
        # Adding output to get the instance id and the private ip
        core.CfnOutput(self, "StressToolEc2Id",value=instance.instance_id)
        core.CfnOutput(self, "StressToolEc2Ip",value=instance.instance_private_ip)



    def __init__(self, scope: core.Stack, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        self.base_platform = BasePlatform(self, self.stack_name)

        self.fargate_task_def = aws_ecs.TaskDefinition(
            self, "TaskDef",
            compatibility=aws_ecs.Compatibility.EC2_AND_FARGATE,
            cpu='256',
            memory_mib='512',
        )

        self.container = self.fargate_task_def.add_container(
            "NodeServiceContainerDef",
            image=aws_ecs.ContainerImage.from_registry("brentley/ecsdemo-nodejs:cdk"),
            memory_reservation_mib=512,
            logging=aws_ecs.LogDriver.aws_logs(
                stream_prefix='ecsworkshop-nodejs'
            ),
            environment={
                "REGION": getenv('AWS_DEFAULT_REGION')
            },
        )

        self.container.add_port_mappings(
            aws_ecs.PortMapping(
                container_port=3000
            )
        )

        self.fargate_service = aws_ecs.FargateService(
            self, "NodejsFargateService",
            service_name='ecsdemo-nodejs',
            task_definition=self.fargate_task_def,
            cluster=self.base_platform.ecs_cluster,
            security_group=self.base_platform.services_sec_grp,
            desired_count=1,
            cloud_map_options=aws_ecs.CloudMapOptions(
                cloud_map_namespace=self.base_platform.sd_namespace,
                name='ecsdemo-nodejs'
            )
        )

        self.fargate_task_def.add_to_task_role_policy(
            aws_iam.PolicyStatement(
                actions=['ec2:DescribeSubnets'],
                resources=['*']
            )
        )
        
        # Enable Service Autoscaling
        # self.autoscale = self.fargate_service.auto_scale_task_count(
        #     min_capacity=1,
        #     max_capacity=10
        # )
        
        # self.autoscale.scale_on_cpu_utilization(
        #     "CPUAutoscaling",
        #     target_utilization_percent=50,
        #     scale_in_cooldown=core.Duration.seconds(30),
        #     scale_out_cooldown=core.Duration.seconds(30)
        # )
        
        # self.stressToolEc2 = self.nodejsTempEc2StressTool()
        
    
    

_env = core.Environment(account=getenv('AWS_ACCOUNT_ID'), region=getenv('AWS_DEFAULT_REGION'))
environment = "ecsworkshop"
stack_name = "{}-nodejs".format(environment)
app = core.App()
NodejsService(app, stack_name, env=_env)
app.synth()
