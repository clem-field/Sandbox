# Converting CIS Benchmarks to InSpec Profiles with SAF CLI

## Overview
The [Security Automation Framework (SAF) CLI](https://saf-cli.mitre.org/), developed by MITRE, is a command-line tool that automates security tasks, 
including converting Center for Internet Security (CIS) Benchmarks in XLSX format into InSpec profiles. InSpec is an open-source compliance testing 
framework that defines security policies as code. SAF CLI generates an InSpec profile "stub" (basic structure with control stubs and metadata) from a 
CIS Benchmark, which requires manual refinement to implement full test logic.

This guide explains how to use SAF CLI to convert a CIS Benchmark XLSX file into an InSpec profile for compliance automation.

## Prerequisites

- **SAF CLI**: Install via npm (requires Node.js 14+):

  ```bash
  npm install -g @mitre/saf
  ```

- **CIS Benchmark File**: Download the CIS Benchmark in XLSX format from the [CIS website](https://www.cisecurity.org/) (e.g., `CIS_Microsoft_Windows_Server_2022_Benchmark_v1.0.0.xlsx`). Ensure it follows the standard CIS column structure.
- **InSpec (Optional)**: For testing the profile, install InSpec via RubyGems:

  ```bash
  gem install inspec
  ```

## Step-by-Step Guide

### 1. Prepare the Input File
- Obtain the CIS Benchmark XLSX file.
- Ensure the file is not password-protected and matches the standard CIS format (e.g., columns like "Recommendation Number", "Title", "Description").

### 2. Build Mapping File


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
  saf generate spreadsheet2inspec_stub -i /path/to/cis-benchmark.xlsx -o /path/to/output/profile
  ```
  - `-i, --input`: Path to the CIS Benchmark XLSX file (required).
  - `-o, --output`: Output directory for the generated profile (defaults to `profile` folder).

- **Additional Options**:
  - `-M, --mapping`: Path to a custom YAML mapping file for non-standard XLSX formats.
  - `-c, --controlNamePrefix`: Prefix for control IDs (e.g., `cis-` for `cis-1-1`).
  - `-f, --format`: Format type (`cis`, `disa`, `general`; use `cis` for CIS Benchmarks).
  - `-m, --metadata`: Path to the JSON metadata file from Step 2.
  - `-s, --singleFile`: Output controls as a single Ruby file (default: separate files).
  - Global flags: `-h` for help, `-L` for log level (e.g., `--logLevel=debug`).

- Example for a CIS Windows Benchmark:
  ```bash
  saf generate spreadsheet2inspec_stub \
    -i ~/downloads/CIS_Windows_Server_2022_v1.0.0.xlsx \
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
  # control 'cis-1-1' do
  #   title 'Ensure auditing is configured'
  #   desc 'Description from CIS'
  #   impact 0.5
  #   # TODO: Implement test logic here
  # end
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

For further assistance, consult the SAF CLI documentation or community support on GitHub.


