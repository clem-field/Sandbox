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
    tag = re.sub(r'\s+', '', tag)  # remove all whitespace first

    # Fix family part: AC-1 → AC-01, but only if it's 1-3 digits after hyphen
    tag = re.sub(r'([A-Za-z]{2,})-(\d{1,3})(?=[^0-9]|$)', lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", tag)

    # Normalize enhancement separators: .a.1, a.1, (a).1, (a)1 → (a)(1)
    # Handle dot notation: AC-01.a.1 or AC-01.a.1.c
    tag = re.sub(r'\.([a-zA-Z])', r'(\1)', tag.lower())  # .a → (a)

    # Handle (a).1 → (a)(1), (a)1 → (a)(1)
    tag = re.sub(r'\(([a-z])\)\.(\d)', r'(\1)(\2)', tag.lower())
    tag = re.sub(r'\(([a-z])\)(\d)', r'(\1)(\2)', tag.lower())

    # Ensure all enhancements are in (x)(y) format with no dots
    def repl(match):
        letters = ''.join(match.groups())
        return '(' + ')( '.join(letters) + ')'

    tag = re.sub(r'\(([a-z]+)\)', repl, tag.lower())

    # Final cleanup: make sure it's like AC-01(a)(1)
    tag = re.sub(r'\((\d+)\)', lambda m: f"({m.group(1)})", tag)

    return tag

def get_latest_ccis_by_nist(df: pd.DataFrame) -> Dict[str, dict]:
    """
    Processes a DataFrame with CCI data and returns a dict where:
    - Key: CCI (e.g., 'CCI-000002')
    - Value: { 'def': definition, 'nist': [list of normalized NIST tags] }
    Only the MOST RECENT (by published_date) record per normalized NIST control is kept.
    """
    if df.empty:
        return {}

    # Ensure published_date is datetime
    df['published_date'] = pd.to_datetime(df['published_date'])

    # Normalize the NIST control tag
    df['nist_normalized'] = df['nist_control_tag'].apply(normalize_nist_control)

    # Keep only the latest record for each (cci, nist_normalized) combo
    df_latest = df.sort_values('published_date').drop_duplicates(
        subset=['cci', 'nist_normalized'], keep='last'
    )

    # Now, for each CCI, collect all unique normalized NIST controls (latest versions)
    result = defaultdict(lambda: {'def': '', 'nist': set()})

    for _, row in df_latest.iterrows():
        cci = row['cci'].strip()
        definition = row['definition'].strip() if pd.notna(row['definition']) else ""
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