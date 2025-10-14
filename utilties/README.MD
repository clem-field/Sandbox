# Terraform Tracking

## Architectural Code Updates

### Example Usage

#### Mermaid

```bash
python tf_arc_diagram.py ./terraform_project -o diagrams/arch --format mermaid --source code
```

Output: diagrams/arch.mmd with Mermaid syntax.

#### Parse Terraform Plan JSON (Graphviz)

```bash
terraform plan -out=tfplan && terraform show -json tfplan > plan.json
python tf_arc_diagram.py plan.json -o diagrams/arch --format graphviz --source plan
```

Output: diagrams/arch.dot with Graphviz syntax.

#### Parse Terraform State JSON (Mermaid)

```bash
python tf_arc_diagram.py terraform.tfstate -o diagrams/arch --format mermaid --source state
```

### Containerization

```Docker
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install python-hcl2

# Install Graphviz for DOT rendering (optional, only if rendering to PNG/SVG)
RUN apt-get update && apt-get install -y graphviz

# Install Mermaid CLI for rendering (optional)
RUN apt-get install -y nodejs npm && npm install -g @mermaid-js/mermaid-cli

# Copy the script
COPY tf_arc_diagram.py .

# Entry point
ENTRYPOINT ["python", "tf_arc_diagram.py"]
```

```bash
docker build -t tf-diagram-gen .
```

### Post-Plan Workflow

```bash
terraform plan -out=tfplan
terraform show -json tfplan > plan.json
docker run -v $(pwd):/app/terraform tf-diagram-gen /app/terraform/plan.json -o /app/terraform/arch --format mermaid --source plan
```

### Post-Apply Workflow

```bash
terraform apply
docker run -v $(pwd):/app/terraform tf-diagram-gen /app/terraform/terraform.tfstate -o /app/terraform/arch --format mermaid --source state
```

#### Optional Mermaid to PNG/SVG

```bash
docker run -v $(pwd):/app/terraform tf-diagram-gen /app/terraform -o /app/terraform/arch --format mermaid --source code
npx @mermaid-js/mermaid-cli -i arch.mmd -o arch.png
```

##### For Graphviz Render with dot

```bash
dot -Tpng arch.dot -o arch.png
```

### CI/CD Integration

```yaml
name: Generate Terraform Diagram
on:
  push:
    branches: [main]
jobs:
  diagram:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: terraform init
      - run: terraform plan -out=tfplan
      - run: terraform show -json tfplan > plan.json
      - uses: docker://tf-diagram-gen
        with:
          args: plan.json -o diagrams/arch --format mermaid --source plan
      - run: npx @mermaid-js/mermaid-cli -i diagrams/arch.mmd -o diagrams/arch.png
      - uses: actions/upload-artifact@v3
        with:
          name: architecture-diagram
          path: diagrams/arch.png
```

## Terraform Variables

usage: tf_var_mapping.py [-h] -i INPUT_DIR [-o OUTPUT_FILE] [-f {json,csv,xlsx,markdown}]

Generate Terraform variable inventory.

options:
  -h, --help            show this help message and exit
  -i INPUT_DIR, --input-dir INPUT_DIR
                        Root directory containing Terraform files to process
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Output file name (without extension)
  -f {json,csv,xlsx,markdown}, --output-format {json,csv,xlsx,markdown}
                        Output format: json, csv, xlsx, or markdown
  -d DIRECTORY, --directory DIRECTORY path to the output directory

### Examples in local use

#### Using short-form arguments

```bash
python script.py -i ./path/to/terraform -o terraform_inventory -f json
```

#### Using long-form arguments (same result)

```bash
python script.py --input-dir ./path/to/terraform --output-file terraform_inventory --output-format json
```

#### Generate CSV output

```bash
python script.py -i ./path/to/terraform -o terraform_inventory -f csv
```

#### Generate XLSX output

```bash
python script.py -i ./path/to/terraform -o terraform_inventory -f xlsx
```

#### Generate Markdown output

```bash
python script.py -i ./path/to/terraform -o terraform_inventory -f markdown
```

### Docker

```docker
FROM python:3.10-slim

# Install dependencies
RUN pip install --no-cache-dir python-hcl2 openpyxl

# Create working directory
WORKDIR /app

# Copy the script and required modules
COPY tf_var_mapping.py /app/tf_var_mapping.py
COPY libraries.py /app/libraries.py
# Uncomment if locals.py is needed
# COPY locals.py /app/locals.py

# Set entrypoint to run the script
ENTRYPOINT ["python", "/app/tf_var_mapping.py"]
```

#### Build

```bash
docker build -t tf-inventory-generator .
```

#### Run Locally

```bash
docker run -v $(pwd)/path/to/terraform:/terraform tf-inventory-generator -i /terraform -o /terraform/inventory -f json
```

### CI/CD Use

```yaml
name: Terraform Pipeline

on:
  push:
    branches: [main]
  pull_request:

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        run: docker build -t tf-inventory-generator .

      - name: Run Terraform Plan
        run: |
          # Assuming your Terraform commands here, e.g.,
          terraform init
          terraform plan -out=plan.tfplan

      - name: Generate Variable Inventory
        run: |
          docker run -v $(pwd):/workspace tf-inventory-generator -i /workspace/path/to/terraform -o /workspace/inventory -f json

      - name: Run Terraform Apply (on main branch only)
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve plan.tfplan

      - name: Upload Inventory Artifact
        uses: actions/upload-artifact@v4
        with:
          name: terraform-inventory
          path: inventory.json  # Adjust based on output
```