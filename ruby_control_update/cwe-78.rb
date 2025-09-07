control "CWE-327" do
  title "The product uses a broken or risky cryptographic algorithm or protocol."

  desc  "rationale", ""
  desc  'check', "[{'Type': 'Language', 'Class': 'Not Language-Specific', 'Prevalence': 'Undetermined'}]"
  desc  'fix', "[{'Phase': ['Implementation'], 'Description': 'Use strong cryptographic algorithms like AES or SHA-256.'}]"

  impact 0.5
  tag severity: 'medium'
  tag nist: ['SC-13']
  tag grc: ['SC-13']
  tag cwe: 'CWE-327'
  tag owasp: ['A02:2021', 'A3:2017']
  tag cci: []
  tag category: 'sast'
  tag org_ref: ['None']
  tag nist_references: ['None']
  tag related_controls: ['SC-8', 'SC-12']

  describe 'Vulnerability locations' do
    it 'should be reviewed at: src/js/nodejs_crypto.js: 4/' do
      skip 'Manual review required for locations: src/js/nodejs_crypto.js: 4/'
    end
  end
end
