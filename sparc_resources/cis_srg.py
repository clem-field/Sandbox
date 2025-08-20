import pandas as pd
from lxml import etree

# Read CSV
df = pd.read_csv('cis_docker_benchmark.csv')

# Create XCCDF root
ns = {'xccdf': 'http://checklists.nist.gov/xccdf/1.2'}
benchmark = etree.Element('{%s}Benchmark' % ns['xccdf'], id='xccdf_org.cisecurity.benchmarks_benchmark_1.6.0_CIS_Docker_Benchmark')
etree.SubElement(benchmark, '{%s}title' % ns['xccdf']).text = 'CIS Docker Benchmark v1.6.0'
etree.SubElement(benchmark, '{%s}version' % ns['xccdf']).text = '1.6.0'
etree.SubElement(benchmark, '{%s}description' % ns['xccdf']).text = 'Compliance checks for Docker containers in ECS Fargate'

# Create Profile
profile = etree.SubElement(benchmark, '{%s}Profile' % ns['xccdf'], id='xccdf_org.cisecurity.benchmarks_profile_Level_3')
etree.SubElement(profile, '{%s}title' % ns['xccdf']).text = 'Level 3 - STIG'
etree.SubElement(profile, '{%s}description' % ns['xccdf']).text = 'STIG-specific controls'

# Add Rules
for index, row in df.iterrows():
    rule = etree.SubElement(benchmark, '{%s}Rule' % ns['xccdf'], id=f'xccdf_org.cisecurity.benchmarks_rule_{row["Rule ID"]}')
    etree.SubElement(rule, '{%s}title' % ns['xccdf']).text = row['Title']
    etree.SubElement(rule, '{%s}description' % ns['xccdf']).text = row['Description']
    etree.SubElement(rule, '{%s}rationale' % ns['xccdf']).text = row['Rationale']
    select = etree.SubElement(profile, '{%s}select' % ns['xccdf'], idref=f'xccdf_org.cisecurity.benchmarks_rule_{row["Rule ID"]}', selected='true')

# Save XCCDF
tree = etree.ElementTree(benchmark)
tree.write('cis_docker_xccdf.xml')