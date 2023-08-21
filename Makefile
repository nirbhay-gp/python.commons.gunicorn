
docker-build:
	.scripts/build-server-image.sh

docker-publish:
	.scripts/publish-server-image.sh

docker-login:
	aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 465495805839.dkr.ecr.ap-south-1.amazonaws.com