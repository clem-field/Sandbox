import pandas as pd

cis_df = pd.read_excel('cis_benchmark.xlsx')
srg_df = pd.DataFrame(columns=['SRGID', 'Requirement', 'Severity', 'Discussion', 'Check', 'Fix', 'CCI'])  # Add more as needed

srg_df['SRGID'] = 'CIS-' + cis_df['Section'].astype(str)
srg_df['Requirement'] = cis_df['Title']
srg_df['Severity'] = cis_df['Profile Applicability'].map({'Level 1': 'Medium', 'Level 2': 'Low'})
srg_df['Discussion'] = cis_df['Rationale'] + ' ' + cis_df['Impact']
srg_df['Check'] = cis_df['Audit']
srg_df['Fix'] = cis_df['Remediation']
srg_df['CCI'] = cis_df['References'].str.extract(r'(CCI-\d+)', expand=False)  # Extract if present

srg_df.to_excel('converted_srg.xlsx', index=False)
