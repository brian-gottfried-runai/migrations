# Run:ai cluster migration script

The script helps automate the task of moving the following objects from one cluster to another:
- Projects
- Departments
- Node Pools
- Access Rules

> [!NOTE]  
Important note:
This script does not apply migration to the default node pool and the default department at the moment.
Please change them manually, before running the script. <br />
> <br />
> Make sure you also have an application API token for system administrator on tenant scope

How to use:
1. copy/clone the file from the repository
2. Install the libraries ```pip install requests dataclasses```
3. Under ```if __name__ == "__main__"``` edit the BASE_URL, CLEINT_ID, CLIENT_SECRET, REALM
4. Under the two ```Cluster()``` objects, edit the ```cluster_id``` to match the cluster id of the current production/old cluster, and the cluster id of the new cluster<br />
> [!WARNING] 
***Make sure to put the correct cluster ID of the production cluster first, and the new cluster second***
5. Run the script:
   ```python3 main.py```
