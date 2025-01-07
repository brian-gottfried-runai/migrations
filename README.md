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
3. First, use the ```retrieve_json.py``` script to get the JSON of the resources from the old cluster. Under the  ```Cluster()``` object in that file, edit the ``` base_url ``` and ```cluster_id``` to match the old cluster and the ```client_id``` and ```client_secret``` to match the Application you set up for that cluster.
4. Next, use the ```restore_json_REST.py``` script to use those JSON files to apply to the new cluster. Under the  ```Cluster()``` object in that file, edit the ``` base_url ``` and ```cluster_id``` to match the old cluster and the ```client_id``` and ```client_secret``` to match the Application you set up for that cluster.
