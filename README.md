# Google Cloud Organization Policies

[![Badge: Google Cloud](https://img.shields.io/badge/Google%20Cloud-%234285F4.svg?logo=google-cloud&logoColor=white)](#readme)
[![Badge: CI](https://github.com/Cyclenerd/google-cloud-org-policies/actions/workflows/build.yml/badge.svg)](https://github.com/Cyclenerd/google-cloud-org-policies/actions/workflows/build.yml)
[![Badge: GitHub](https://img.shields.io/github/license/cyclenerd/google-cloud-org-policies)](https://github.com/Cyclenerd/google-cloud-org-policies/blob/master/LICENSE)

This webapp lists the available Organization Policy constraints for Google Cloud Platform.

I built it so that I can quickly search for organization policy constraints by ID, name and description.
The official [Google Documentation](https://cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints) is too slow and messy for me.

## 🧑‍💻 Development

If you want to customize or run this webapp on your local computer,
you need the following requirements.

### Requirements

* [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`) – only used to mint an access token
* Python 3 (`python3`) – standard library only, no Google Cloud SDK / client libraries
* Perl 5 (`perl`)
* Perl modules:
	* [JSON::XS](https://metacpan.org/pod/JSON::XS)
	* [Template::Toolkit](https://metacpan.org/pod/Template::Toolkit)
	* [plackup](https://metacpan.org/dist/Plack/view/script/plackup)

<details>
<summary><b>Debian/Ubuntu</b></summary>

Packages:

```shell
sudo apt update
sudo apt install \
	libjson-xs-perl \
	libtemplate-perl \
	libplack-perl
```

[Google Cloud CLI](https://cloud.google.com/sdk/docs/install#deb):

```shell
sudo apt-get install apt-transport-https ca-certificates gnupg
# Add the gcloud CLI distribution URI as a package source
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# Import the Google Cloud public key.
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo tee /usr/share/keyrings/cloud.google.gpg
# Update and install the gcloud CLI
sudo apt-get update
sudo apt-get install google-cloud-cli
```
</details>

<details>
<summary><b>macOS</b></summary>

Homebrew packages:

```shell
brew install perl
brew install cpanminus pkg-config
brew install --cask google-cloud-sdk
```

Perl modules:

```shell
cpanm --installdeps .
```
</details>

Build catalog:

The catalog is fetched from the Organization Policy v2 REST API
(`constraints.list`) using only `urllib.request` (no Google Cloud SDK).
You need to provide a parent resource (organization, folder or project) and
have the `orgpolicy.constraints.list` IAM permission on it.

```shell
cd build
gcloud auth list
# Pass the parent via --organization / --folder / --project
# (or the GCLOUD_ORGANIZATION / GCLOUD_FOLDER / GCLOUD_PROJECT env vars).
python3 list_org_policies.py \
	--organization "123456789012" \
	--token "$(gcloud auth print-access-token)"
```

This writes:

* `policies.json` – list of `{id, name, description}` objects
* `policies.txt` – sorted constraint IDs (used to detect catalog changes)

Build website:

```bash
perl build.pl
```

Run:

```shell
plackup --host "127.0.0.1" --port "8080"
```

## ❤️ Contributing

Have a patch that will benefit this project?
Awesome! Follow these steps to have it accepted.

1. Please read [how to contribute](CONTRIBUTING.md).
1. Fork this Git repository and make your changes.
1. Create a Pull Request.
1. Incorporate review feedback to your changes.
1. Accepted!


## 📜 License

All files in this repository are under the [Apache License, Version 2.0](LICENSE) unless noted otherwise.

Portions of this webapp are modifications based on work created and shared by [Google](https://developers.google.com/readme/policies)
and used according to terms described in the [Creative Commons 4.0 Attribution License](https://creativecommons.org/licenses/by/4.0/).
