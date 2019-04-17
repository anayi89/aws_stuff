import boto3, os, subprocess, sys, time
from boto3.session import Session

def connect_to_aws():
    global ec2_resource, ec2_client, my_name, session

    my_name = os.getlogin()
    cred_file = "~/.aws/credentials"
    config_file = "~/.aws/config"
    command1 = " | awk -F' ' 'FNR == 2 {print $3}'"
    command2 = " | awk -F' ' 'FNR == 3 {print $3}'"

    # Run shell commands that extract AWS credentials from the AWS CLI configuration files.
    # Convert the output to strings.
    access_key = subprocess.Popen("cat " + cred_file + command1,
                    shell=True,
                    stdout=subprocess.PIPE).communicate()[0].splitlines()[0]
    
    secret_key = subprocess.Popen("cat " + cred_file + command2,
                    shell=True,
                    stdout=subprocess.PIPE).communicate()[0].splitlines()[0]

    region = subprocess.Popen("cat " + config_file + command1,
                    shell=True,
                    stdout=subprocess.PIPE).communicate()[0].splitlines()[0]

    session = Session(
        aws_access_key_id='{}'.format(access_key),
        aws_secret_access_key='{}'.format(secret_key),
        region_name='{}'.format(region)
    )

    # Connect to the AWS EC2 service.
    ec2_resource = session.resource('ec2')
    ec2_client = session.client('ec2')

def create_ssh_key():
    global key_name

    key_filepath = '/home/{}/.aws_keys'.format(my_name)
    key_name = raw_input("Enter a name for your SSH key: ")

    aws_key = ec2_resource.create_key_pair(KeyName=key_name)
    local_key = str(aws_key.key_material)

    # Create a hidden directory and a .pem file on the local machine.
    # Store the SSH key in the .pem file.
    subprocess.Popen('mkdir {}'.format(key_filepath), shell=True, stdout=subprocess.PIPE)
    local_key_file = open('{0}/{1}.pem'.format(key_filepath, key_name), 'w')
    local_key_file.write(local_key)
    local_key_file.close()

def set_up_ec2_instance():
    global sec_group, subnet

    # Create a virtual private network.
    vpc = ec2_resource.create_vpc(
        CidrBlock='192.168.0.0/16',
    )
    vpc.wait_until_available()

    # Create a virtual router and attach the VPN to it.
    ig = ec2_resource.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=ig.id)

    # Create a route table and public route for the VPN.
    route_table = vpc.create_route_table()
    route_table.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=ig.id
    )

    # Create a subnet and attach it to the VPN.
    subnet = ec2_resource.create_subnet(
        CidrBlock='192.168.0.0/24',
        VpcId=vpc.id
    )

    # Associate the route table with the subnet.
    route_table.associate_with_subnet(SubnetId=subnet.id)

    # Create a security group and attach it to the VPN.
    sec_group = ec2_resource.create_security_group(
        GroupName='security_group',
        Description='A security group for the WordPress blog.',
        VpcId=vpc.id
    )

    # Create inbound firewall rules in the security group.
    # Permit HTTP and SSH traffic.
    ec2_client.authorize_security_group_ingress(
        GroupId=sec_group.group_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )

def create_ec2_instance():
    global wordpress_blog

    wordpress_blog = ec2_resource.create_instances(
        ImageId='ami-0dccf86d354af8ce3',
        MinCount=1,
        MaxCount=1,
        KeyName=key_name,
        InstanceType='t2.micro',
        NetworkInterfaces=
        [
            {
                'DeviceIndex': 0,
                'SubnetId': subnet.id,
                'AssociatePublicIpAddress': True,
                'Groups': [sec_group.group_id]
            }
        ]
    )

def get_wordpress_url():
    wordpress_blog[0].wait_until_running()
    wordpress_blog[0].reload()

    global instance_id

    public_ip = wordpress_blog[0].public_ip_address
    instance_id = wordpress_blog[0].instance_id
    
    print "WordPress Blog URL: http://{}/wp-login.php".format(public_ip)

def get_username_and_pass():
    print "Wait a few minutes for the instance to fully load."
    t = 180
    while t >= 0:
        sys.stdout.write('\r{} '.format(t))
        t -= 1
        sys.stdout.flush()
        time.sleep(1)

    instance = ec2_resource.Instance('{}'.format(instance_id))
    output = instance.console_output()
    print output['Output'].split('#########################################################################')[1]

def main():
    connect_to_aws()
    create_ssh_key()
    set_up_ec2_instance()
    create_ec2_instance()
    get_wordpress_url()
    get_username_and_pass()

if __name__ == "__main__":
    main()
