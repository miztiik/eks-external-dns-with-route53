from aws_cdk import aws_eks as _eks
from aws_cdk import aws_sqs as _sqs
from aws_cdk import aws_iam as _iam
from aws_cdk import core as cdk

from stacks.miztiik_global_args import GlobalArgs


class EksExternalDnsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        stack_log_level: str,
        eks_cluster,
        clust_oidc_provider_arn,
        clust_oidc_issuer,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add your stack resources below):


        #######################################
        #######                         #######
        #######   K8s Service Account   #######
        #######                         #######
        #######################################

        svc_accnt_name = "external-dns"
        svc_accnt_ns = "default"

        # To make resolution of LHS during runtime, pre built the string.
        oidc_issuer_condition_str = cdk.CfnJson(
            self,
            "oidc-issuer-str",
            value={
                f"{clust_oidc_issuer}:sub": f"system:serviceaccount:{svc_accnt_ns}:{svc_accnt_name}"
            },
        )

        # Svc Account Role
        self._external_dns_provider_role = _iam.Role(
            self,
            "external-dns-svc-accnt-role",
            assumed_by=_iam.FederatedPrincipal(
                federated=f"{clust_oidc_provider_arn}",
                conditions={
                    "StringEquals": oidc_issuer_condition_str
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"
            ),
            # managed_policies=[
            #     _iam.ManagedPolicy.from_aws_managed_policy_name(
            #         "AmazonSQSFullAccess"
            #     )
            # ]
        )

        # Allow CW Agent to create Logs
        self._external_dns_provider_role.add_to_policy(_iam.PolicyStatement(
            actions=[
                "route53:ChangeResourceRecordSets"
            ],
            resources=["arn:aws:route53:::hostedzone/*"]
        ))

        self._external_dns_provider_role.add_to_policy(_iam.PolicyStatement(
            actions=[
                "route53:ListHostedZones",
                "route53:ListResourceRecordSets"
            ],
            resources=["*"]
        ))


        _external_dns_provider_svc_accnt_manifest = {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": f"{svc_accnt_name}",
                "namespace": f"{svc_accnt_ns}",
                "annotations": {
                    "eks.amazonaws.com/role-arn": f"{self._external_dns_provider_role.role_arn}"
                }
            }
        }

        _external_dns_provider_svc_accnt = _eks.KubernetesManifest(
            self,
            f"{svc_accnt_name}",
            cluster=eks_cluster,
            manifest=[
                _external_dns_provider_svc_accnt_manifest
            ]
        )


        ###########################################
        ################# OUTPUTS #################
        ###########################################
        output_0 = cdk.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page.",
        )

        output_1 = cdk.CfnOutput(
            self,
            "ExternalDnsProviderRole",
            value=f"{self._external_dns_provider_role.role_arn}",
            description="External DNS Provider Role"
        )


