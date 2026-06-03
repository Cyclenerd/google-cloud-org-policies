#!/usr/bin/env perl

# Copyright 2023-2026 Nils Knieling. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

use strict;
use warnings;
use JSON::XS;
use Template;
use File::Copy;

my $import_policies_json = "policies.json";
my $export_policies_json = "../web/policies.json";

print "Please wait...\n";

# JSON

mkdir('../web/');

open(POLICIES_JSON, '<', $import_policies_json) or die "$import_policies_json: $!";
my $json = "";
while (my $row = <POLICIES_JSON>) {
	chomp $row;
	$json .= $row;
}
close(POLICIES_JSON);
my $policies_scalar = JSON::XS->new->utf8->decode($json);

my @policies_list = ();
foreach my $policy (@{$policies_scalar}) {
	my $policy_id          = $policy->{'id'}          || '???';
	my $policy_name        = $policy->{'name'}        || '-';
	my $policy_description  = $policy->{'description'} || '-';
	$policy_name        =~ s/^\s//; # Remove beginning white space
	$policy_description =~ s/^\s//; # Remove beginning white space
	push(@policies_list, {
		id    => $policy_id,
		name  => $policy_name,
		desc  => $policy_description,
	});
}

# Export normalized catalog for the webapp.
open(POLICIES, '>', $export_policies_json) or die "$export_policies_json: $!";
my $policies_json = JSON::XS->new->utf8->encode(\@policies_list);
print POLICIES $policies_json;
close(POLICIES);

# PAGE

my $gmttime   = gmtime();
my $timestamp = time();

my $template = Template->new(
	INCLUDE_PATH => './src',
	PRE_PROCESS  => 'config.tt2',
	VARIABLES => {
		'gmttime'          => $gmttime,
		'timestamp'        => $timestamp,
		'gitHubServerUrl'  => $ENV{'GITHUB_SERVER_URL'} || '',
		'gitHubRepository' => $ENV{'GITHUB_REPOSITORY'} || '',
		'gitHubRunId'      => $ENV{'GITHUB_RUN_ID'}     || '',
	}
);

$template->process('index.tt2',  { 'policies' => \@policies_list }, '../web/index.html')  || die "Template process failed: ", $template->error(), "\n";
$template->process('robots.txt', {},                               '../web/robots.txt')  || die "Template process failed: ", $template->error(), "\n";
$template->process('404.tt2',    {},                               '../web/404.html')    || die "Template process failed: ", $template->error(), "\n";

copy('./src/img/favicon/favicon.ico',          '../web/favicon.ico');
copy('./src/img/favicon/favicon-16x16.png',    '../web/favicon-16x16.png');
copy('./src/img/favicon/favicon-32x32.png',    '../web/favicon-32x32.png');
copy('./src/img/favicon/apple-touch-icon.png', '../web/apple-touch-icon.png');

print "DONE\n";
