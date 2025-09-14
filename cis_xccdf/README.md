# Converting CIS Benchmarks to InSpec Profiles with SAF CLI

## Overview
The [Security Automation Framework (SAF) CLI](https://saf-cli.mitre.org/), developed by MITRE, is a command-line tool that automates security tasks, 
including converting Center for Internet Security (CIS) Benchmarks in XLSX format into InSpec profiles. InSpec is an open-source compliance testing 
framework that defines security policies as code. SAF CLI generates an InSpec profile "stub" (basic structure with control stubs and metadata) from a 
CIS Benchmark, which requires manual refinement to implement full test logic.

This guide explains how to use SAF CLI to convert a CIS Benchmark XLSX file into an InSpec profile for compliance automation.

## Prerequisites

- **SAF CLI**: Install via npm (requires Node.js 14+) or use a docker image

  ```bash
  npm install -g @mitre/saf
  ```

	or

	```bash
	docker pull mitre/saf
  ```

- **CIS Benchmark File**: Download the CIS Benchmark in XLSX format from the [CIS website](https://www.cisecurity.org/) 
	- (e.g., `CIS_Microsoft_Windows_Server_2022_Benchmark_v1.0.0.xlsx`). 
	- Ensure it follows the standard CIS column structure.
- **InSpec (Optional)**: For testing the profile, install InSpec via RubyGems:

  ```bash
  gem install inspec
  ```

## Step-by-Step Guide

### 1. Prepare the Input File

Obtain the CIS Benchmark XLSX file. Ensure the file is not password-protected and matches the standard CIS format (e.g., columns like 
"Recommendation Number", "Title", "Description").

### 2. Build Mapping File

The mapping file, in YAML, is used to define which columns from the CSV/XLSX file will be used for the required fields (see below) 
of the inspec profile control file. The mapping file should be created and updated to allow for a more robust mapping which improves
the applicabitlity of spreadsheets (e.g. vendor checklists, benchmarks, other security documentation) to be converted into a
profile. This expands the use of profiles for comparison of technical checks and control coverage by a specific implementation.

Mapping file example:

```yaml
id:                           # Required
  - ID
  - "recommendation #"
title:                        # Required
  - Title                     # You can give more than one column header as a value for an
  - title                     # attribute if you are not sure how it will be spelled in the input.
desc:
  - Description
  - Discussion
  - description
impact: 0.5                  # If impact is set, its value will be used for every control
desc.rationale:
  - Rationale
  - rationale statement
desc.check:                   # Required
  - Audit
  - audit procedure
desc.fix:
  - Remediation
  - remediation procedure
desc.additional_information:  # You can define arbitrary values under desc and tag
  - Additional Information    # if you have extra fields to record
desc.default_value:
  - Default Value
ref:                          # InSpec keyword - saf will check this column for URLs (links to documentation)
  - References                # and record each address as a ref attribute

# source: https://saf-cli.mitre.org/#mapping-files
```

Where the keys (title) are InSpec control attributes and the values (- Title) are the column headers in the 
input spreadsheet that correspond to that attribute


### 3. Generate InSpec Metadata (Optional but Recommended)

- Create a metadata template for the `inspec.yml` file to define maintainer details, version, license, etc.
- Run:

  ```bash
  saf generate inspec_metadata -o cis_metadata.json
  ```

- Edit `cis_metadata.json` with your details, e.g.:

  ```json
  {
    "maintainer": "Your Organization",
    "copyright": "Your Organization",
    "copyright_email": "security@yourorg.com",
    "license": "Proprietary",
    "version": "1.0.0"
  }
  ```

### 4. Generate the InSpec Profile Stub

- Use the `spreadsheet2inspec_stub` command to convert the XLSX into an InSpec profile stub.
- Basic command:

  ```bash
  saf generate spreadsheet2inspec_stub -i /path/to/cis-benchmark.xlsx -M /path/to/mapping/file -m path/to/metadata/file -o /path/to/output/profile
  ```

| Required 	| option 	| alternate 					| 							Function																												|
|-----------|---------|---------------------|------------------------------------------------------------------------------|
|		Y				| 	-i		| --input							| Path to the CIS Benchmark XLSX file (required). 														|
|		Y				| 	-o		| --output						| Output directory for the generated profile (defaults to `profile` folder).	|
|		Y				|		-M		| --mapping						| Path to a custom YAML mapping file for non-standard XLSX formats.						|
|		Y				|		-m		| --metadata					| Path to the JSON metadata file from Step 2.																		|
|		N				|		-c		| --controlNamePrefix	| Prefix for control IDs (e.g., `cis-` for `cis-1-1`).													|
|		N				|		-f		| --format						| Format type (`cis`, `disa`, `general`; use `cis` for CIS Benchmarks).				|
|		N				|		-s		| --singleFile				| Output controls as a single Ruby file (default: separate files).						|
| Global		|		-h		|											| help																																					|
| Global		|		-L		|											| log level (e.g., `--logLevel=debug`).																					|

- Example for a CIS Windows Benchmark:

  ```bash
  saf generate spreadsheet2inspec_stub \
    -i ~/downloads/CIS_Windows_Server_2022_v1.0.0.xlsx \
    -M ~/projects/inspec_metadata.json \
    -o ~/projects/cis-windows-profile \
    -f cis \
    -c cis-win \
    -m cis_metadata.json
  ```

- **Output**: A profile folder (e.g., `cis-windows-profile`) containing:
  - `inspec.yml`: Profile metadata.
  - `controls/`: Stub files for each CIS control (e.g., `cis-1-1.rb`).
  - Other InSpec structure files (e.g., `libraries/`).

### 5. Review and Refine the Generated Stub

- The generated profile is a **stub** with skeletal controls (e.g., empty `describe` blocks with titles and descriptions).
- Example stub:

  ```ruby
  control 'cis-1-1' do
     title 'Ensure auditing is configured'
     desc 'Description from CIS'
     impact 0.5
     # TODO: Implement test logic here
   end
  ```
- Manually add InSpec test logic using resources like `registry_key` for Windows checks. Refer to [InSpec documentation](https://docs.chef.io/inspec/).

### 6. Test the Profile

- Run the profile against a target system:
  ```bash
  inspec exec /path/to/output/profile --target local://
  ```
  - For remote targets: `--target ssh://user@host`.
- Review the compliance report for passed/failed/skipped controls.

## Troubleshooting

### XLSX Parsing Issues

Verify the file format or provide a custom YAML mapping file (see SAF CLI docs).

### PDF Benchmarks

Use InspecTools' `pdf2inspec` for PDFs, as SAF CLI is optimized for XLSX.

### Debugging

 Use `--logLevel=debug` for detailed logs.

## Limitations

- Generates stubs only; full test logic requires manual implementation.
- Some CIS controls (e.g., manual reviews) are not automatable.
- For DISA STIGs, use CSV exports with `-f disa`.

## Resources
- [SAF CLI Documentation](https://saf-cli.mitre.org/)
- [InSpec Documentation](https://docs.chef.io/inspec/)
- [CIS Benchmarks](https://www.cisecurity.org/)
- [MITRE SAF GitHub](https://github.com/mitre/saf)




