import pandas as pd
import re
import numpy as np

def extract_nist_info(text):
    """
    Extract NIST Revision and Control(s) from the references or additional information text.
    Handles multiple controls like 'CM-7, CM-8'.
    Assumes format like 'NIST SP 800-53 Rev. 5: CM-7, ...'
    Returns tuple (rev, controls_str) where controls_str is comma-separated.
    """
    if pd.isna(text):
        return '', ''
    
    text_str = str(text)
    # Find Rev
    rev_match = re.search(r'NIST SP 800-53 Rev\. (\d+)', text_str)
    rev = rev_match.group(1) if rev_match else ''
    
    # Find all NIST controls after the rev part
    if rev and rev_match:
        after_rev = text_str[rev_match.end():]
        controls = re.findall(r'([A-Z]{2,3}-\d+(?:\.\d+)?)', after_rev)
    else:
        controls = []
    
    controls_str = ', '.join(controls) if controls else ''
    return rev, controls_str

# Read the org_list.xlsx file, 'org' sheet
org_df = pd.read_excel('org_list.xlsx', sheet_name='org')

# Read the CIS Example.xlsx file, 'Sheet1' sheet
cis_df = pd.read_excel('CIS Example.xlsx', sheet_name='Sheet1')

# Perform left join on 'Control ID' from org_df to 'Recommendation #' from cis_df
# This adds all CIS columns to org_df where matches are found
joined_df = pd.merge(org_df, cis_df, left_on='Control ID', right_on='Recommendation #', how='left')

# Extract NIST Rev and Control from 'References' column, falling back to 'Additional Information' if NaN
def get_nist_ref(row):
    ref = row['References']
    add_info = row['Additional Information']
    # Use References first, then Additional Information
    text = ref if not pd.isna(ref) else add_info
    return extract_nist_info(text)

# Apply extraction
nist_extractions = joined_df.apply(get_nist_ref, axis=1, result_type='expand')
joined_df['NIST Rev'] = nist_extractions[0]
joined_df['NIST Control'] = nist_extractions[1]

# Optionally, drop the duplicate 'Key_0' if merge creates it (pandas internal), but usually not needed
# Save the updated dataframe back to an Excel file (new file to avoid overwriting originals)
output_file = 'updated_org_list.xlsx'
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    joined_df.to_excel(writer, sheet_name='org', index=False)

print(f"Updated file saved as '{output_file}'")
print("Join completed. Rows in updated sheet:", len(joined_df))
print("Sample NIST extractions:")
print(joined_df[['Control ID', 'NIST Rev', 'NIST Control']].head())