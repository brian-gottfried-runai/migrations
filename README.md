# Run:ai cluster migration script

The script helps automate the task of moving the following objects from one cluster to another:
- Projects
- Departments
- Node Pools
- Access Rules
- Compute Assets
- Environment Assets
- Workload Templates
- Datasources
- Policies
- Interactive Workloads
- Training Workloads (not yet implemented)

> [!NOTE]  
Important note:
This script does not apply migration to the default node pool and the default department at the moment.
Please change them manually, before running the script. <br />
> <br />
> Make sure you also have an application API token for system administrator on tenant scope in each cluster

How to use:
1. clone the repository
2. Install the libraries ```pip install requests dataclasses```
3. First, use the ```retrieve_json.py``` script to get the JSON of the resources from the old cluster. You will have to set the ```--base_url```, ```--client_id```, ```--client_secret```, and ```--cluster_id``` arguments when you call the script.
4. Next, use the ```restore_json_REST.py``` script to use those JSON files to apply to the new cluster. You will have to set the ```--base_url```, ```--client_id```, ```--client_secret```, and ```--cluster_id``` arguments when you call the script. If you are migrating all of the PVCs created by Runai from the old cluster to the new cluster, you can also set  ```--convert_new_pvc_datasources_to_existing```, which will convert any PVC datasources that created a new PVC into datasources that expect an existing PVC with the generated name.
