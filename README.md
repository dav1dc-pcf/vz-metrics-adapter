# Vizceral Metrics Adapter

This project acts as the literal translation layer between the data presented from each foundation by [app-metrics-nozzle](https://github.com/dav1dc-pcf/app-metrics-nozzle) so that it can be be transformed it into the data model expected by [vizceral-app-metrics-ui](https://github.com/dav1dc-pcf/vizceral-app-metrics-ui)

## Configuration

Configuration is relatively straight forward using contsants and variables at the top of `index.py` 

The Notices thresholds for information/warning/danger can be modified by tweaking the following constants:

```
# Constants for warning checks
THRESHOLD_CPU_DANGER      = 75
THRESHOLD_CPU_CRIT        = 50
THRESHOLD_CPU_WARN        = 25

THRESHOLD_RPS_DANGER      = 1000
THRESHOLD_RPS_CRIT        = 500
THRESHOLD_RPS_WARN        = 100

# The next 2 sets of thresholds are expressed as % used
THRESHOLD_MEM_DANGER      = 90
THRESHOLD_MEM_CRIT        = 75
THRESHOLD_MEM_WARN        = 60

THRESHOLD_DISK_DANGER     = 90
THRESHOLD_DISK_CRIT       = 80
THRESHOLD_DISK_WARN       = 75

# Add a notice to the node if not in the state defined below
THRESHOLD_RUNNING_STATE   = "RUNNING"
```

The configuration for each foundation one wishes to visualize (or for each installation of **app-metrics-nozzle**) is set like so:

```
# First Foundation
pcf_one = {}
pcf_one["name"] = "pcf-secondary"
pcf_one["displayName"] = "Secondary PCF"
pcf_one["json_url"] = "https://app-metrics-nozzle.apps.your-pcf.com/api/apps"
pcf_one["exclude_orgs"] = []
pcf_one["only_orgs"] = ["second-foundation"]

# Second Foundation (which is really just the first, repeated with different filters)
pcf_two = {}
pcf_two["name"] = "pcf-primary"
pcf_two["displayName"] = "Primary PCF"
pcf_two["json_url"] = "https://app-metrics-nozzle.apps.your-pcf.com/api/apps"
pcf_two["exclude_orgs"] = ["system", "second-foundation"]
pcf_two["only_orgs"] = []
```

Note that **** and **** can be used to include/exclude ORGs to reduce some of the "clutter" in the visualization.

Finally, ensure that ever Foundation you have defined has been packed into the array which will be iterated over to build the final data model:

```
# Pack the list of foundations to process into the hash "foundations"
foundations[pcf_one["name"]] = pcf_one
foundations[pcf_two["name"]] = pcf_two

#
# END Configuration
#
```

Once fully configured, push an insance to your PCF/CF, and then ensure you have deployed [vizceral-app-metrics-ui](https://github.com/dav1dc-pcf/vizceral-app-metrics-ui).
