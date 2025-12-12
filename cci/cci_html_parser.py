import libraries as lib
import make_files as mf
import locals as var

def normalize_nist_control(tag: str) -> str:
    """
    Normalize different formats of NIST 800-53 controls to a standard form:
    Examples:
      'AC-1 a 1'          → 'AC-01(a)(1)'
      'AC-01.a.1'         → 'AC-01(a)(1)'
      'AC-01(a).1'        → 'AC-01(a)(1)'
      'AC-1(a)(1)'        → 'AC-01(a)(1)'
      'ac-2 (b)(3)'       → 'AC-02(b)(3)'   (also uppercases family)
    """
    if not tag or not isinstance(tag, str):
        return ""

    tag = tag.strip().upper()

    # Remove extra spaces and normalize separators
    tag = lib.re.sub(r'\s+', '', tag)  # remove all whitespace first

    # Fix family part: AC-1 → AC-01, but only if it's 1-3 digits after hyphen
    tag = lib.re.sub(r'([A-Za-z]{2,})-(\d{1,3})(?=[^0-9]|$)', lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", tag)

    # Normalize enhancement separators: .a.1, a.1, (a).1, (a)1 → (a)(1)
    # Handle dot notation: AC-01.a.1 or AC-01.a.1.c
    tag = lib.re.sub(r'\.([a-zA-Z])', r'(\1)', tag.lower())  # .a → (a)

    # Handle (a).1 → (a)(1), (a)1 → (a)(1)
    tag = lib.re.sub(r'\(([a-z])\)\.(\d)', r'(\1)(\2)', tag.lower())
    tag = lib.re.sub(r'\(([a-z])\)(\d)', r'(\1)(\2)', tag.lower())

    # Ensure all enhancements are in (x)(y) format with no dots
    def repl(match):
        letters = ''.join(match.groups())
        return '(' + ')( '.join(letters) + ')'

    tag = lib.re.sub(r'\(([a-z]+)\)', repl, tag.lower())

    # Final cleanup: make sure it's like AC-01(a)(1)
    tag = lib.re.sub(r'\((\d+)\)', lambda m: f"({m.group(1)})", tag)

    return tag

def get_latest_ccis_by_nist(df: lib.pd.DataFrame) -> lib.Dict[str, dict]:
    """
    Processes a DataFrame with CCI data and returns a dict where:
    - Key: CCI (e.g., 'CCI-000002')
    - Value: { 'def': definition, 'nist': [list of normalized NIST tags] }
    Only the MOST RECENT (by published_date) record per normalized NIST control is kept.
    """
    if df.empty:
        return {}

    # Ensure published_date is datetime
    df['published_date'] = lib.pd.to_datetime(df['published_date'])

    # Normalize the NIST control tag
    df['nist_normalized'] = df['nist_control_tag'].apply(normalize_nist_control)

    # Keep only the latest record for each (cci, nist_normalized) combo
    df_latest = df.sort_values('published_date').drop_duplicates(
        subset=['cci', 'nist_normalized'], keep='last'
    )

    # Now, for each CCI, collect all unique normalized NIST controls (latest versions)
    result = lib.defaultdict(lambda: {'def': '', 'nist': set()})

    for _, row in df_latest.iterrows():
        cci = row['cci'].strip()
        definition = row['definition'].strip() if lib.pd.notna(row['definition']) else ""
        nist_norm = row['nist_normalized']

        # Use the most recent definition for this CCI (in case multiple)
        if result[cci]['def'] == "":  # or compare dates if needed
            result[cci]['def'] = definition

        if nist_norm:
            result[cci]['nist'].add(nist_norm)

    # Convert sets to sorted lists for consistent output
    final_result = {}
    for cci, data in result.items():
        final_result[cci] = {
            'def': data['def'],
            'nist': sorted(list(data['nist']))
        }

    return final_result

print(f"Parsing html from {var.SCRIPT_DIR}")
for tr in var.TRS:
    ref =[]
    info = tr.text
    info = info.splitlines()
    # print(info) ### Used for testing, uncomment as needed
    try:
        if info.index('CCI:') > 0:
            cci_id = info[info.index('CCI:')+1]
            # print(cci_id) ### Used for testing, uncomment as needed
    except:
        next
    # row = [cci_id, cci_status, contrib, published, defined, ref]
    # cci_list.append(row)
    try:
        if info.index('Status:') > 0:
            cci_status = info[info.index('Status:')+1]
            # print(cci_status) ### Used for testing, uncomment as needed
    except:
        next
    try:
        if info.index('Contributor:') > 0:
            contrib = info[info.index('Contributor:')+1]
            # print(contrib) ### Used for testing, uncomment as needed
    except:
        next
    try:
        if info.index('Published Date:') > 0:
            published = info[info.index('Published Date:')+1]
            # print(published) ### Used for testing, uncomment as needed
    except:
        next
    try:
        if info.index('Definition:') > 0:
            defined = info[info.index('Definition:')+1]
            # print(defined) ### Used for testing, uncomment as needed
    except:
        next
    try:
        tds = tr.find_all('td')
        for td in tds:
            refs = td.text
            refs = refs.splitlines()
            if any('NIST:' in sub for sub in refs)==True:
                refer = str([item for item in refs if 'NIST:' in item])
                refer = refer.replace("[","")
                refer = refer.replace("]","")
                refer = refer.replace("'","")
                refer.split(':')
                refer = str(refer)
                refer = refer.replace("NIST: ", "")
                # ref.append(refer)
                ref = refer
                # print(ref) ### Used for testing, uncomment as needed
    except:
        next
    if len(ref) > 0:
        print(f" Adding row to CCI_LIST")
        row = [cci_id, cci_status, contrib, published, defined, ref]
        var.CCI_LIST.append(row)

# print(len(cci_list))
# cci_list
print("Cleaning up lists")
cci_df = lib.pd.DataFrame(var.CCI_LIST, columns=var.CCI_COLS)
cci_df[['refer_version', 'nist_control_tag']] = cci_df['references'].str.split(':', expand=True)
cci_df['cci'] = cci_df['cci'].str.lstrip()
cci_df['published_date'] = cci_df['published_date'].str.lstrip()
cci_df['published_date'] = lib.pd.to_datetime(cci_df['published_date'], format='%Y-%m-%d')
cci_df['published_date'] = cci_df['published_date'].dt.date
cci_df['definition'] = cci_df['definition'].str.lstrip()
cci_df['references'] = cci_df['references'].str.lstrip()
cci_df['refer_version'] = cci_df['refer_version'].str.lstrip()
cci_df['nist_control_tag'] = cci_df['nist_control_tag'].str.lstrip()

cci_df = cci_df.drop(['status', 'contributor'], axis=1)
 
print("Generating various outputs")
cci_rev4 = cci_df[cci_df['refer_version'] == 'NIST SP 800-53 Revision 4 (v4)']
cci_rev4.sort_values('published_date').drop_duplicates('nist_control_tag', keep='last')
cci_rev5 = cci_df[cci_df['refer_version'] == 'NIST SP 800-53 Revision 5 (v5)']
cci_rev5.sort_values('published_date').drop_duplicates('nist_control_tag', keep='last')
cci_53a = cci_df[cci_df['refer_version'] == "NIST SP 800-53A (v1)"]
cci_53a.sort_values('published_date').drop_duplicates('nist_control_tag', keep='last')

# Create json
cci_rev4_json=get_latest_ccis_by_nist(cci_rev4)
cci_rev5_json=get_latest_ccis_by_nist(cci_rev5)
cci_53a_json=get_latest_ccis_by_nist(cci_53a)

# cci_df

try:
    print(f"Checking for output Directory {var.OUTPUT_FOLDER}")
    mf.output_dir_validation()
    print(f"Directory {var.OUTPUT_FOLDER} is good ✅")
except:
    print(f"❌Unable to find or create {var.OUTPUT_FOLDER}")

try:
    mf.write_df_to_excel(cci_df, var.OUTPUT_FOLDER, var.COMPLETE_CCI)
    print(f"✅ Successfully updated: ", var.OUTPUT_FOLDER + var.COMPLETE_CCI)
except:
    print(f"❌ Unable to write: ", var.OUTPUT_FOLDER + var.COMPLETE_CCI)

try:
    mf.write_df_to_excel(cci_rev4, var.OUTPUT_FOLDER, var.REV4_CCI )
    print(f"✅ Successfully updated: ", var.OUTPUT_FOLDER + var.REV4_CCI)
except:
    print(f"❌ Unable to write: ", var.OUTPUT_FOLDER + var.REV4_CCI)

try:
    mf.write_df_to_excel(cci_rev5, var.OUTPUT_FOLDER, var.REV5_CCI)
    print(f"✅ Successfully updated: ", var.OUTPUT_FOLDER + var.REV5_CCI)
except:
    print(f"❌ Unable to write: ", var.OUTPUT_FOLDER + var.REV5_CCI)

try:
    mf.write_df_to_excel(cci_53a, var.OUTPUT_FOLDER, var.PART_A_CCI)
    print(f"✅ Successfully updated: ", var.OUTPUT_FOLDER + var.PART_A_CCI)
except:
    print(f"❌ Unable to write: ", var.OUTPUT_FOLDER + var.PART_A_CCI)