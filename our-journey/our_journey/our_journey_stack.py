from aws_cdk import (
    Duration,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_i,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    CfnOutput,
    CustomResource,
)
import aws_cdk as cdk
from cdklabs.generative_ai_cdk_constructs import bedrock, s3vectors
from constructs import Construct

class OurJourneyStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create an S3 bucket to store documents
        doc_bucket = s3.Bucket(
            self, 
            'DocBucket',
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Create a Bedrock Vector Knowledge Base
        kb = bedrock.VectorKnowledgeBase(
            self, 
            "knowledgebase",
            embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_256,
            vector_store=s3vectors.VectorIndex(
                self, 
                "vectorstore",
                dimension=256,
                vector_bucket=s3vectors.VectorBucket(
                    self, 
                    "vector-bucket",
                    removal_policy=cdk.RemovalPolicy.DESTROY,
                    auto_delete_objects=True
                ),
                non_filterable_metadata_keys=[
                    "AMAZON_BEDROCK_TEXT", 
                    "AMAZON_BEDROCK_METADATA"
                ]
            )
        )

        kb.add_s3_data_source(
            bucket=doc_bucket,
            data_deletion_policy=bedrock.DataDeletionPolicy.RETAIN
        )

        # Create bedrock guardrails
        guardrail = bedrock.Guardrail(
            self,
            "guardrail",
            name=f"our-journey-guardrail-{self.stack_name}",
            blocked_input_messaging="Your request cannot be processed as it violates our content policies. (Su solicitud no puede ser procesada ya que viola nuestras políticas de contenido.)",
            blocked_outputs_messaging="Your request cannot be processed as it violates our content policies. (Su solicitud no puede ser procesada ya que viola nuestras políticas de contenido.)",
            content_filters=[
                bedrock.ContentFilter(
                    input_strength=bedrock.ContentFilterStrength.MEDIUM,
                    output_strength=bedrock.ContentFilterStrength.MEDIUM,
                    type=bedrock.ContentFilterType.SEXUAL,
                    input_action=bedrock.GuardrailAction.BLOCK,
                    input_enabled=True,
                    output_action=bedrock.GuardrailAction.BLOCK,
                    output_enabled=True
                ),
                bedrock.ContentFilter(
                    input_strength=bedrock.ContentFilterStrength.MEDIUM,
                    output_strength=bedrock.ContentFilterStrength.MEDIUM,
                    type=bedrock.ContentFilterType.VIOLENCE,
                    input_action=bedrock.GuardrailAction.BLOCK,
                    input_enabled=True,
                    output_action=bedrock.GuardrailAction.BLOCK,
                    output_enabled=True
                ),
                bedrock.ContentFilter(
                    input_strength=bedrock.ContentFilterStrength.MEDIUM,
                    output_strength=bedrock.ContentFilterStrength.MEDIUM,
                    type=bedrock.ContentFilterType.HATE,
                    input_action=bedrock.GuardrailAction.BLOCK,
                    input_enabled=True,
                    output_action=bedrock.GuardrailAction.BLOCK,
                    output_enabled=True
                ),
                bedrock.ContentFilter(
                    input_strength=bedrock.ContentFilterStrength.MEDIUM,
                    output_strength=bedrock.ContentFilterStrength.MEDIUM,
                    type=bedrock.ContentFilterType.INSULTS,
                    input_action=bedrock.GuardrailAction.BLOCK,
                    input_enabled=True,
                    output_action=bedrock.GuardrailAction.BLOCK,
                    output_enabled=True
                ),
                bedrock.ContentFilter(
                    input_strength=bedrock.ContentFilterStrength.MEDIUM,
                    output_strength=bedrock.ContentFilterStrength.MEDIUM,
                    type=bedrock.ContentFilterType.MISCONDUCT,
                    input_action=bedrock.GuardrailAction.BLOCK,
                    input_enabled=True,
                    output_action=bedrock.GuardrailAction.BLOCK,
                    output_enabled=True
                ),
                bedrock.ContentFilter(
                    input_strength=bedrock.ContentFilterStrength.MEDIUM,
                    output_strength=bedrock.ContentFilterStrength.NONE,
                    type=bedrock.ContentFilterType.PROMPT_ATTACK,
                    input_action=bedrock.GuardrailAction.BLOCK,
                    input_enabled=True,
                )
            ]
        )


        # ======================================================================
        # DYNAMODB TABLES
        # ======================================================================
        
        # Conversations Table - stores all user conversations with the chatbot
        conversations_table = dynamodb.Table(
            self,
            "ConversationsTable",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
        )

        # GSI for querying by userId
        conversations_table.add_global_secondary_index(
            index_name="UserIdIndex",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI for querying by flag status
        conversations_table.add_global_secondary_index(
            index_name="FlagIndex",
            partition_key=dynamodb.Attribute(
                name="flag",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
        )

        # Follow-Up Queue Table - stores conversations that need follow-up
        followup_table = dynamodb.Table(
            self,
            "FollowUpTable",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
        )

        # GSI for querying by status
        followup_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI for querying by priority
        followup_table.add_global_secondary_index(
            index_name="PriorityIndex",
            partition_key=dynamodb.Attribute(
                name="priority",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI for querying by requestType (normal vs crisis)
        followup_table.add_global_secondary_index(
            index_name="RequestTypeIndex",
            partition_key=dynamodb.Attribute(
                name="requestType",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
        )


        # County Resources Table - maps NC county names to their PDF S3 keys and source URLs
        # Written by the scraper Lambda, read by the PDF serve Lambda
        county_resources_table = dynamodb.Table(
            self,
            "CountyResourcesTable",
            partition_key=dynamodb.Attribute(
                name="county",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
        )

        # Create a WebSocket API
        web_socket_api = apigwv2.WebSocketApi(self, "web_socket_api",)
        apigwv2.WebSocketStage(
            self, 
            "stage",
            web_socket_api=web_socket_api,
            stage_name="prod",
            auto_deploy=True
        )


        bedrock_orchestration = _lambda.Function(
            self,
            "bedrock-orchestration-lambda",
            runtime = _lambda.Runtime.PYTHON_3_12,
            code = _lambda.Code.from_asset(
                "./lambdas/bedrock_orchestration",
            ),
            handler = "lambda_function.lambda_handler",
            timeout = Duration.minutes(15),
            environment={
                "API_GATEWAY_URL": web_socket_api.api_endpoint,
                "KNOWLEDGE_BASE_ID": kb.knowledge_base_id,
                "NUM_KB_RESULTS": "5",
                "GUARDRAIL_ID": guardrail.guardrail_id,
                "GUARDRAIL_VERSION": guardrail.guardrail_version,
                "CONVERSATIONS_TABLE": conversations_table.table_name,
                "FOLLOWUP_TABLE": followup_table.table_name,
            }
        )

        # Grant necessary permissions to the Lambda function
        bedrock_orchestration.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
        )
        bedrock_orchestration.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonAPIGatewayInvokeFullAccess")
        )
        bedrock_orchestration.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess")
        )
        bedrock_orchestration.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:OurJourneyStack-*"]
            )
        )

        

        #api gateway integrations
        web_socket_api.add_route(
            "sendMessage",
            integration = apigwv2_i.WebSocketLambdaIntegration("bedrock-orchestration", bedrock_orchestration),
            return_response=True
        )

        # ======================================================================
        # SCRAPER LAMBDA LAYER
        # ======================================================================
        scraper_layer = _lambda.LayerVersion(
            self,
            "ScraperLayer",
            code=_lambda.Code.from_asset("./lambdas/layers/scraper-layer.zip"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Web scraping dependencies (requests, BeautifulSoup4)"
        )

        # ======================================================================
        # SCRAPER LAMBDA IAM ROLE
        # ======================================================================
        scraper_role = iam.Role(
            self,
            "ScraperLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for OurJourney scraper and sync Lambda"
        )

        # S3 permissions for doc bucket
        scraper_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3BucketAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:ListBucket",
                    "s3:DeleteObject",
                    "s3:PutObject",
                ],
                resources=[
                    doc_bucket.bucket_arn,
                    f"{doc_bucket.bucket_arn}/*"
                ]
            )
        )

        # Bedrock Agent permissions for knowledge base sync
        scraper_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ListDataSources",
                    "bedrock:StartIngestionJob",
                    "bedrock:GetIngestionJob",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/{kb.knowledge_base_id}",
                    f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/{kb.knowledge_base_id}/*"
                ]
            )
        )

        # DynamoDB permissions for county resources table (scoped, not full access)
        scraper_role.add_to_policy(
            iam.PolicyStatement(
                sid="CountyResourcesDynamoDBAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                ],
                resources=[county_resources_table.table_arn]
            )
        )

        # CloudWatch Logs permissions
        scraper_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # ======================================================================
        # SCRAPER LAMBDA FUNCTION
        # ======================================================================
        scraper_lambda = _lambda.Function(
            self,
            "ScraperLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("./lambdas/scraper_lambda"),
            role=scraper_role,
            timeout=Duration.minutes(15),  # Maximum timeout for scraping and ingestion
            memory_size=512,  # Extra memory for faster processing
            layers=[scraper_layer],
            environment={
                "DOC_BUCKET_NAME": doc_bucket.bucket_name,
                "KNOWLEDGE_BASE_ID": kb.knowledge_base_id,
                "COUNTY_RESOURCES_TABLE": county_resources_table.table_name,
            },
            description="Scrapes OurJourney website and syncs Knowledge Base"
        )

        # ======================================================================
        # CUSTOM RESOURCE FOR INITIAL SCRAPE
        # ======================================================================
        # Custom resource to trigger initial scrape on stack creation
        scraper_custom_resource = CustomResource(
            self,
            "ScraperCustomResource",
            service_token=scraper_lambda.function_arn,
            properties={
                "Trigger": "StackDeploy"
            }
        )

        # Ensure custom resource runs after knowledge base is created
        scraper_custom_resource.node.add_dependency(kb)
        scraper_custom_resource.node.add_dependency(doc_bucket)

        # ======================================================================
        # EVENTBRIDGE RULE FOR WEEKLY SCRAPING
        # ======================================================================
        # Schedule: Every Sunday at midnight EST (5 AM UTC)
        scraper_schedule_rule = events.Rule(
            self,
            "ScraperScheduleRule",
            rule_name="ourjourney-weekly-scraper",
            description="Weekly web scraping and Knowledge Base sync for OurJourney",
            schedule=events.Schedule.cron(
                minute="0",
                hour="5",  # 5 AM UTC = midnight EST
                week_day="SUN"
            ),
        )

        # Add Lambda as target
        scraper_schedule_rule.add_target(
            targets.LambdaFunction(scraper_lambda)
        )

        # ======================================================================
        # ADMIN RETRIEVAL LAMBDA
        # ======================================================================
        admin_lambda = _lambda.Function(
            self,
            "AdminRetrievalLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("./lambdas/admin_retrieval"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "CONVERSATIONS_TABLE": conversations_table.table_name,
                "FOLLOWUP_TABLE": followup_table.table_name,
            },
            description="Admin Lambda for retrieving conversation and follow-up data"
        )

        # Grant DynamoDB full access to admin lambda
        admin_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess")
        )

        # ======================================================================
        # REST API GATEWAY FOR ADMIN
        # ======================================================================
        rest_api = apigw.RestApi(
            self,
            "AdminRestApi",
            rest_api_name="OurJourney Admin API",
            description="REST API for admin access to conversations and follow-ups",
            deploy_options=apigw.StageOptions(
                stage_name="prod"
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        # Lambda integration
        admin_integration = apigw.LambdaIntegration(
            admin_lambda,
            proxy=True
        )

        # API Routes - Conversations
        conversations_resource = rest_api.root.add_resource("conversations")
        conversations_resource.add_method("GET", admin_integration)  # List all conversations
        
        conversation_by_id = conversations_resource.add_resource("{id}")
        conversation_by_id.add_method("GET", admin_integration)  # Get specific conversation
        conversation_by_id.add_method("PUT", admin_integration)  # Update conversation (e.g., flag status)

        # API Routes - Follow-ups
        followups_resource = rest_api.root.add_resource("followups")
        followups_resource.add_method("GET", admin_integration)  # List all follow-ups
        
        followup_by_id = followups_resource.add_resource("{id}")
        followup_by_id.add_method("GET", admin_integration)  # Get specific follow-up
        followup_by_id.add_method("PUT", admin_integration)  # Update follow-up (status, assignment, notes)

        CfnOutput(self, "websocket-url",
            value = web_socket_api.api_endpoint,
        )

        CfnOutput(self, "doc-bucket-name",
            value = doc_bucket.bucket_name,
        )


        CfnOutput(self, "knowledge-base-id",
            value = kb.knowledge_base_id,
        )

        CfnOutput(self, "scraper-lambda-arn",
            value = scraper_lambda.function_arn,
            description="ARN of the scraper Lambda function"
        )

        CfnOutput(self, "scraper-schedule-rule",
            value = scraper_schedule_rule.rule_name,
            description="EventBridge rule for weekly scraping"
        )

        CfnOutput(self, "conversations-table-name",
            value = conversations_table.table_name,
            description="DynamoDB table for conversations"
        )

        CfnOutput(self, "county-resources-table-name",
            value = county_resources_table.table_name,
            description="DynamoDB table mapping NC counties to their PDF resource guides"
        )

        CfnOutput(self, "followup-table-name",
            value = followup_table.table_name,
            description="DynamoDB table for follow-up queue"
        )

        CfnOutput(self, "admin-api-url",
            value = rest_api.url,
            description="REST API endpoint for admin operations"
        )

        CfnOutput(self, "admin-lambda-arn",
            value = admin_lambda.function_arn,
            description="ARN of the admin retrieval Lambda function"
        )