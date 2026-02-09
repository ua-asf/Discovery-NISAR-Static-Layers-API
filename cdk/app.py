#!/usr/bin/env python3

# from https://docs.aws.amazon.com/cdk/v2/guide/serverless_example.html
import aws_cdk as cdk
from static_layers_api import CdkStaticLayersStack
import os

app = cdk.App()

env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
)
CdkStaticLayersStack(
    app,
    env=env,
    description="NISAR Static Layers Stack",
    construct_id="CdkStaticLayersStack",
    deployment_environment="test",
)

app.synth()
