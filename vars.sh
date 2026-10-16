export AWS_PAGER=""
export NAME=rg
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ROLE_NAME=orchestrator-lambda-role-$NAME
export DOMAIN_NAME=orchestrator-search-$NAME
export BUCKET=lambda-deploy-$ACCOUNT_ID-$NAME
