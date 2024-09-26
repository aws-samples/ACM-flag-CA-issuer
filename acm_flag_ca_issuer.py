import boto3
import botocore
import json
import argparse
import csv
args = argparse.ArgumentParser()
args.add_argument(
    '--profile',
    type=str,
    default=None,
    help="Use the specified AWS credentials profile.  By default not used")
args.add_argument(
    '--output',
    type=str,
    default='text',
    choices=[
        'json',
        'csv',
        'text'],
    help="By Default results are printed to the console.  You can also save them to json or csv")
args.add_argument(
    '--regions',
    type=list,
    default=None,
    help="Comma separated list of AWS regions to iterate over.  Default is all")
args.add_argument(
    '--flagged-ca',
    type=str,
    required=True,
    help="Comma separated list of flagged CAs")

args = args.parse_args()

args.flagged_ca_list = args.flagged_ca.split(',')

if args.profile is None:
    session = boto3.Session()
else:
    session = boto3.Session(profile_name=args.profile)

if args.regions is None:
    args.regions = session.get_available_regions('acm')

results = []
for region_name in args.regions:
    acm_client = session.client('acm', region_name=region_name)
    try:
        certificates = acm_client.list_certificates()['CertificateSummaryList']
    except botocore.exceptions.ClientError as err:
        if err.response['Error']['Code'] == 'UnrecognizedClientException':
            continue
    for certificate in certificates:        
        certificate_arn = certificate['CertificateArn']
        
        certificate_detail = acm_client.describe_certificate(CertificateArn=certificate_arn)['Certificate']
        cert_issuer = certificate_detail.get('Issuer', "")        
        issued_at = certificate_detail.get('IssuedAt',"")
        if issued_at:
            issued_at = issued_at.strftime('%Y-%m-%d %H:%M:%S')
        results.append({
            "domain_name": certificate_detail.get('DomainName', ""),
            "alternate_domain_names": ','.join(certificate_detail.get('SubjectAlternativeNames', [])),
            "issued_at": issued_at,
            "not_before": certificate_detail.get('NotBefore').strftime('%Y-%m-%d %H:%M:%S'),
            "cert_issuer": cert_issuer,
            "flagged_ca": cert_issuer in args.flagged_ca_list
        })
if args.output == 'csv':
    with open('flagged_acm_cs.csv', 'w', newline='') as csvfile:
        fieldnames = ['domain_name', 'alternate_domain_names', 'issued_at', 'not_before', 'cert_issuer', 'flagged_ca']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)
elif args.output == 'json':
    with open('flagged_acm_cs.json', 'w') as jsonfile:
        json.dump(results, jsonfile, indent=4, default=str)
elif args.output == 'text':
    print(json.dumps(results, indent=4))