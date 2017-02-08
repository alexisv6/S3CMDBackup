import boto3
import botocore
import sys
import os
import argparse

# Asks user whether they want to create new bucket
# Returns true or false, continues until valid input
def prompt_create_bucket():
    while True:
        accept = input('Would you like to create bucket [Y/N]:')
        if accept == 'Y' or accept == 'y':
            return True
        elif accept == 'N' or accept == 'n':
            return False
        else:
            print("Invalid Input: Try Again")

def print_separator():
    print('==========================================')
    return

# Prints the introduction and variables passed in
def print_intro(path, bucket):
    print('Welcome to CMD Backup')
    print('Backup Path: ' + path)
    print('AWS Bucket: ' + bucket)
    print_separator()
    return

# Creates an AWS Bucket
def create_bucket(s3, bucketname):
    while True:
        print('Trying to Create Bucket: ' + bucketname)
        try:
            s3.create_bucket(Bucket = bucketname, CreateBucketConfiguration = {'LocationConstraint': 'us-west-2'})
            print(bucketname + ' Bucket Created')
            print_separator()
            return bucketname
        except botocore.exceptions.ClientError as  err:
            print_separator()
            print(err.response['Error']['Message'])
            bucketname = input('Enter a New Bucket Name: ')

# Check if file exist on AWS first
def does_file_exist(s3, bucketname, keyname):
    try:
        object = s3.Object(bucketname, keyname).load()
        return True
    except botocore.exceptions.ClientError as err:
        if err.response['Error']['Code'] == '404':
            print(filename + " Does not exist")
            return False
        else:
            print('Error Connecting to S3...Try Again')
            sys.exit()

# Upload a file to S3
def upload_file(s3, bucketname, keyname, path):
    print('Uploading to S3...', end = '')
    try:
        s3.Object(bucketname, keyname).put(Body=open(path, 'rb'))
        print('Success')
        return True
    except botocore.exceptions.ClientError as err:
        print('Failed')
        print(err.response)
        return False

# Normalize and get folder name
def get_base_foldername(path):
    normed = os.path.normpath(path)
    return os.path.basename(normed)

# Normalize file path to correctly create folders when uploading
def get_s3_keyname(path, backupdir, filename):
    printout = 'Local File Path: ' + path + '/' + filename
    print(printout.replace('//', '/'))
    base_folder = get_base_foldername(backupdir)
    reduced = path.replace(backupdir, base_folder + '/') + '/' + filename
    keyname = reduced.replace('//', '/')
    print('S3 Location: ' + keyname)
    return keyname

# Check Object Summary for size change
def is_size_equal(s3, bucketname, keyname, path):
    object_summary = s3.ObjectSummary(bucketname, keyname)
    s3_size = object_summary.size
    file_size = os.path.getsize(path)
    return s3_size == file_size

# Check for proper directory
def is_dir(path):
    exists = os.path.isdir(path)
    return exists

# Get a valid dir from user
def get_valid_dir():
    while True:
        print('Invalid Directory Entered')
        new_dir = input('Enter A New Directory: ')
        if is_dir(new_dir):
            print('Directory Set: ' + new_dir)
            print_separator()
            return new_dir

## Start is here - Validate Needed Arguments ##
parser = argparse.ArgumentParser(description = 'Validate Arguments Passed In')
parser.add_argument('backup_path', help = 'Please Enter a Path To Backup')
parser.add_argument('bucket_name', help = 'Add a Target Bucket')
args = parser.parse_args()
# Get Arguments
backupDir = args.backup_path.replace('\\', '/')
targetbucket = args.bucket_name
print_intro(backupDir, targetbucket)
valid_dir = is_dir(backupDir)
if not valid_dir:
    backupDir = get_valid_dir().replace('\\','/')
if not backupDir.endswith('/'):
    backupDir = backupDir + '/'
# Prepare S3
print('Checking Bucket Status...')
s3 = boto3.resource("s3");
# Check for correct bucket
try:
    s3.meta.client.head_bucket(Bucket = targetbucket)
    print('**S3 Bucket Found**')
except botocore.exceptions.ClientError as err:
    err_code = int(err.response['Error']['Code'])
    if err_code == 404:
        print("Bucket entered not found")
        shouldcreate = prompt_create_bucket()
        if shouldcreate:
            targetbucket = create_bucket(s3, targetbucket)
        else:
            print('Bucket is needed to backup')
            sys.exit()

# Get Bucket Reference
theBucket = s3.Bucket(targetbucket)
print_separator()
print("Backup To S3 Started")
for path, dirnames, filenames in os.walk(backupDir):
    path = path.replace('\\', '/')
    if not path.endswith('/'):
                path = path + "/"
    for filename in filenames:
        keyname = get_s3_keyname(path, backupDir, filename)
        exists = does_file_exist(s3, targetbucket, keyname)
        if not exists:
            upload_file(s3, targetbucket, keyname, path + filename)
        else:
            print('File Exists...Checking for Differences...')
            equal = is_size_equal(s3, targetbucket, keyname, path + filename)
            if not equal:
                print('Found Difference...Reupload')
                upload_file(s3, targetbucket, keyname, path + filename)
            else:
                print('File is up to date')
        print_separator()
print('Thank you for using CMDBackup')