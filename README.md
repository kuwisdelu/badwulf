# Badwulf 

## Minimal manager for Beowulf clusters and scientific data

The goal of __badwulf__ is a provide a minimal command line interface for accessing and managing project data on scientific computing servers and Beowulf clusters.

This tool is __not__ intended to replace true cluster management and scheduling software for such as __SLURM__. Instead, __badwulf__ is a lightweight package for simplying tasks such as:

- Connecting an port forwarded SSH session to a research server behind a login server

- Managing a simple repository of project data and metadata

- Searching project metadata for terms and keywords

- Syncing projects between work sites like a local client and a research server

## Contents

Jump to a section:

- [Overview](#Overview)
- [Managing projects](#Managing-projects)
- [Querying projects](#Querying-projects)
- [Syncing projects](#Syncing-projects)
- [Site configuration](#Site-configuration)

## Overview

### Installation

You can install __badwulf__ via `pip`, `uv`, etc. For example, using `uv`:

```
uv tool install badwulf
```

This installs a command line utility `wulf` on `$PATH`.

You can see available commands by running `wulf` or `wulf --help`.

### Projects and metadata

By default, if no site configuration is detected, __badwulf__ will set up a prefix under `$HOME/.badwulf`. Any directory under a designated prefix can be a project.

Projects are simply directories with a "metadata.toml" file.

The "metadata.toml" file describes the project, which looks like:

```
name = "example0"
scope = "public"
group = "Example"
title = "This is an example title"
date.created = 1970-01-01
date.updated = 1970-01-01
keywords = ["example", "documentation"]
formats = []
contact = [
	{name = "Bad Wolf", email = "entity@the-moment.time"}
]
description.abstract = """\
	A description of the scientific research project, \
	including the purpose why any data was collected, \
	and the overall goals of the investigation.\
	"""
description.sample-processing = """\
	Describe the sample preparation and \
	the data collection protocol.\
	"""
description.data-processing = """\
	Describe any computational processing \
	applied to the data or files.\
	"""
reference.doi = "not.a.valid.doi/or.is.it"
reference.url = "bad.wolf.corporation"
```

You can use custom keys for any of the sub-tables like "description" and "reference"; "abstract", "url", "doi", etc. are just examples.

Only `name`, `scope`, and `group` are REQUIRED.

Project names MUST be unique after casefolding. Project names, scopes, and groups SHOULD be valid path components. If you let __badwulf__ manage projects for you, these fields are used to create the project directories. A project's canonical path is `PREFIX/SCOPE/GROUP/NAME`.

## Managing projects

### Create and edit project metadata

You can use `wulf` to initialize and edit project metadata.

```
wulf add test --scope private --group scratch
wulf edit test
```

This will initialize a project named "test" by creating the file "PREFIX/private/scratch/test/metadata.toml". If you let __badwulf__ set up a default site configuration for you (i.e., you don't set $BADWULF_SITES), then PREFIX="$HOME/.badwulf/". The next line will open your default text editor (falls back to `vi`) to edit the "metadata.toml" file.

### Check for issues

You can check for various issues using `wulf check`. These include checking for malformed "metadata.toml" files and misplaced project directories.

Use `wulf check --fix` to re-organize a prefix by moving project directories to their canonical locations if they're misplaced.

## Querying projects

### List projects

Use `wulf list` (alias: `wulf ls`) to list the available projects. You can sort and filter the projects using options.

For example, the command below will list projects using a long (`-l`) format that also shows project sizes and modification times, sorted in reverse (`-r`) by size.

```
wulf list -l -r size
```

You can list projects available other sites (e.g., a remote server or cluster) if you've fetched their manifests:

```
wulf list -S <site-alias>
```

### Search project metadata

Use `wulf search` (alias: `wulf grep`) to query project metadata using regular expressions. You can sort and filter the results using the same options as `wulf list`.

For example, the command below will search for the variations of "single cell", "single-cell", etc., in the keywords or description fields, ignoring case (`-i`), limiting results to projects with a "public" scope.

```
wulf search -i 'single.cell' -f keywords -f description -g public
```

You can also search project metadata in manifests from other sites:

```
wulf search -S <site-alias> 'arthritis'
```

## Syncing projects

### Fetch project manifests

Use `wulf fetch` to get project manifests from another site. This will make their project metadata available locally for querying, and let you know what projects are available for syncing.

```
wulf fetch <site-alias>
```

You should always fetch a manifest before pushing a project to another site, so you can inspect if the project has changed at the other site:

```
wulf info <project-name> --diff <site-alias>
```

### Push and pull

Use `wulf push` and `wulf pull` to synchronize project data between sites.

```
wulf fetch origin
wulf push origin test
wulf pull origin hello
```

The above commands (1) fetch the manifest from a site aliased as `origin` (which may be a research server, a cluster's transfer node, etc.), (2) upload a project named "test", and then (3) download a project named "hello".

### Synchronization status

Use `wulf status` to check the synchronization status of projects across all sites that share the same prefix.

Consider the following output:

```
local: /home/user/.badwulf

origin:
-test
+hello
~foo
~bar
```

First, this prints the prefix path for the local site (aliased "local"). Then it shows that a remote site (aliased "origin") does *not* have the project "test" (that *does* exist locally), but it *does* have the project "hello" (that does *not* exist locally), and the projects "foo" and "bar" differ in size, modification time, or metadata between sites.

Only projects that differ between sites are printed. Use `wulf status -v` to also print unified diffs of the metadata for projects that differ between sites (those marked "~").

## Site configuration

### Configure work sites

Use `wulf site` to add or remove work site configurations or edit their variables.

For example:

```
wulf site add origin
wulf site set origin --user="badwulf"
wulf site set origin --host=default:bad.wolf.corporation
wulf site set origin --path=default:/projects
```

This adds a site aliased as "origin". You connect to the site "origin" via SSH as `badwulf@bad.wolf.corporation`. The default prefix at site "origin" is located at `/projects`.

A site can have multiple hosts, and __badwulf__ supports multiple prefixes.

For example, the fully specified `pull` and `push` commands are:

```
wulf pull SITE:HOST PREFIX:PROJECT
```

Each site can have a "default" host and a "default" prefix that will be used if these are left unspecified.

Both of the following commands are equivalent; they download a project named "test" under the "default" prefix from site "origin" using its "default" host:

```
wulf pull origin:default default:test
wulf pull origin test
```

All hosts at the same site are assumed to have prefixes in the same locations. They may even share a filesystem. However, manifests for each host are fetched separately, so they do not need to share storage. If a site has no hosts, the local filesystem is accessed, and SSH uses "localhost" if required.

All project names under the same prefix must be unique (*after* casefolding), so you can use different prefixes as a way to organize projects into namespaces.

### Configure with JSON

The `wulf site` command edits a JSON file typically named "badwulf-sites.json".

Whenever executed, `wulf` looks for "$BADWULF_SITES", "$HOME/.badwulf-sites.json", and "$HOME/.badwulf/badwulf-sites.json" in that order, and creates the last one by default if none are found.

You can create or edit the JSON configuration directly. For example:

```
{
    "local": {
        "user": "",
        "paths: {
            "default": "/home/user/"
        }
    },
    "origin": {
        "user": "badwulf",
        "paths": {
            "default": "/projects"
        },
        "hosts": {
            "default": "bad.wolf.corporation"
        }
    }
}
```

## Environment variables

You can use `$BADWULF_SITES` to provide a path for the site configuration JSON.

You can use `$BADWULF_LOCAL` to set the name of the "local" site. This defaults to "local", but you can use any name for the "local" site. (Any hosts in the "local" site are ignored. The local filesystem is accessed, and SSH uses "localhost" if required.)

