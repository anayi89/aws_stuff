import boto3, os, subprocess
from boto3.session import Session

def connect_to_aws():
	access_key_command = subprocess.Popen("cat ~/.aws/credentials | awk -F' ' 'FNR == 2 {print $3}'", shell=True, stdout=subprocess.PIPE)
	access_key = access_key_command.communicate()[0].splitlines()[0]

	secret_key_command = subprocess.Popen("cat ~/.aws/credentials | awk -F' ' 'FNR == 3 {print $3}'", shell=True, stdout=subprocess.PIPE)
	secret_key = secret_key_command.communicate()[0].splitlines()[0]

	region_command = subprocess.Popen("cat ~/.aws/config | awk -F' ' 'FNR == 2 {print $3}'", shell=True, stdout=subprocess.PIPE)
	region = region_command.communicate()[0].splitlines()[0]

	global session
	session = Session(
		aws_access_key_id='{}'.format(access_key),
		aws_secret_access_key='{}'.format(secret_key),
		region_name='{}'.format(region)
	)

def connect_to_aws_ec2():
	global ec2_resource, ec2_client

	ec2_resource = session.resource('ec2')
	ec2_client = session.client('ec2')

def create_hidden_dir():
	global key_filepath

	my_name = os.getlogin()
	key_filepath = '/home/{}/.aws_keys'.format(my_name)
	subprocess.Popen('mkdir {}'.format(key_filepath), shell=True, stdout=subprocess.PIPE)

def create_ssh_key():
	global key_name, local_key

	key_name = 'example_key'
	aws_key = ec2_resource.create_key_pair(KeyName=key_name)
	local_key = str(aws_key.key_material)

def save_ssh_key():
	key_file = open('{0}/{1}.pem'.format(key_filepath, key_name), 'w')
	key_file.write(local_key)
	key_file.close()

def verify_ssh_key():
	ssh_key = ec2_client.describe_key_pairs(KeyNames=['{}'.format(key_name)])
	print ssh_key
	subprocess.Popen(['echo', 'Your key is located here:'])
	subprocess.Popen(['ls', '-R','{}'.format(key_filepath)])

def main():
	connect_to_aws()
	connect_to_aws_ec2()
	create_hidden_dir()
	create_ssh_key()
	save_ssh_key()
	verify_ssh_key()

if __name__ == '__main__':
	main()