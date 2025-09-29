### High

- [ ] SV-257779
  - [ ] Check that a banner is displayed at the command line login screen with the following command
  - [ ] sudo cat /etc/issue
  - [ ] fix: Edit the "/etc/issue" file to replace the default text with the standard mandatory notice anc consent banner

### Medium

- [ ] SV-257794
  - [ ] verify that grub 2 is configured to enable page poisoning to mitigate use-after-free vulnerabilities
  - [ ] fix: Edit the "/etc/issue" file to replace the default text with the standard mandatory notice anc consent banner

### Low

- [ ] SV-257795
  - [ ] check that kernel page-table isolation is enabled by default to persist in kernel updates
  - [ ] fix: add or modify the following line in "/etc/default/grub" to ensure teh configuration survives updates

### Profile Errors