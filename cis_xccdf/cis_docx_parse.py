import argparse
import docx
import pandas as pd

def parse_docx_table(doc_path):
    doc = docx.Document(doc_path)
    for table in doc.tables:
        # Get headers
        headers = [cell.text.strip() for cell in table.rows[0].cells if cell.text.strip()]
        expected_headers = ['Item #', 'Configuration Item', 'Action / Recommended Parameters', 'Rational/Remediation', 'Windows', 'Unix', 'Level & score']
        if headers[:len(expected_headers)] == expected_headers:
            # This is the target table
            data = []
            for row in table.rows[1:]:
                cells = row.cells
                if len(cells) < 7:
                    continue
                item_num = cells[0].text.strip()
                if not item_num:  # Skip empty rows
                    continue
                config_item = cells[1].text.strip()
                action = cells[2].text.strip()
                rat_rem = cells[3].text.strip()
                windows = cells[4].text.strip()
                unix = cells[5].text.strip()
                level_score = cells[6].text.strip()
                
                # Split rat_rem into rationale, remediation, audit
                rationale = ''
                remediation = ''
                audit = ''
                parts = rat_rem.split('\n')
                current = None
                for line in parts:
                    line = line.strip()
                    if not line:
                        continue
                    lower_line = line.lower()
                    if lower_line.startswith('rationale:') or lower_line.startswith('rational:'):
                        current = 'rationale'
                        rationale = line.split(':', 1)[1].strip() if ':' in line else ''
                    elif lower_line.startswith('remediation:'):
                        current = 'remediation'
                        remediation = line.split(':', 1)[1].strip() if ':' in line else ''
                    elif lower_line.startswith('audit:'):
                        current = 'audit'
                        audit = line.split(':', 1)[1].strip() if ':' in line else ''
                    elif current:
                        if current == 'rationale':
                            rationale += ' ' + line
                        elif current == 'remediation':
                            remediation += ' ' + line
                        elif current == 'audit':
                            audit += ' ' + line
                
                data.append({
                    'Item #': item_num,
                    'Configuration Item': config_item,
                    'Action / Recommended Parameters': action,
                    'Rationale': rationale.strip(),
                    'Remediation': remediation.strip(),
                    'Audit': audit.strip(),
                    'Windows': windows,
                    'Unix': unix,
                    'Level / Score': level_score
                })
            
            if data:
                df = pd.DataFrame(data)
                output_path = doc_path.replace('.docx', '_parsed.xlsx')
                df.to_excel(output_path, index=False)
                print(f"Spreadsheet saved to {output_path}")
                return
    print("No matching table found in the document.")

def main():
    parser = argparse.ArgumentParser(description="Parse a CIS DOCX file and convert specified table to Excel.")
    parser.add_argument('-i', '--input', required=True, help="Path to the input DOCX file")
    args = parser.parse_args()
    
    if not args.input.endswith('.docx'):
        print("Error: Input file must be a .docx file")
        return
    
    parse_docx_table(args.input)

if __name__ == "__main__":
    main()