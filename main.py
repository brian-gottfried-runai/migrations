import requests
from dataclasses import dataclass

@dataclass
class Cluster:
    base_url: str
    client_id: str
    client_secret: str
    realm: str
    cluster_id: str

    def generate_api_token(self):
        payload = f"grant_type=client_credentials&client_id={self.client_id}&client_secret={self.client_secret}"
        headers = {'content-type': "application/x-www-form-urlencoded"}
        url = f"{self.base_url}/auth/realms/{self.realm}/protocol/openid-connect/token"
        try:
            response = requests.post(url=url, data=payload, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            if "access_token" not in response_json:
                raise SystemExit(f"failed to get access token from response. response body={response_json}")

            return response_json["access_token"]

        except requests.exceptions.HTTPError as err:
            print(f"failed to get api token. err={err}")
            raise SystemExit(err)
        except requests.exceptions.JSONDecodeError as err:
            print(f"failed to decode json response. err={err}")
            raise SystemExit(err)


def build_node_pool_resources_from_json(json_data, node_pools_map):
    return             {
                "nodePool": {
                    "name": json_data["nodePool"]["name"],
                    "id": node_pools_map[json_data["nodePool"]["name"]],
                },
                "gpu": {
                    "deserved": json_data["gpu"]["deserved"],
                    "maxAllowed": json_data["gpu"]["maxAllowed"],
                    "overQuotaWeight": json_data["gpu"]["overQuotaWeight"]
                },
            }

def build_node_pool_schema_from_json(json_data):
    return {
        "id": json_data["id"],
        "name": json_data["name"],
        "overProvisioningRatio": 1,
        "labelKey": json_data["labelKey"],
        "labelValue": json_data["labelValue"],
        "placementStrategy": {
            "cpu": json_data["placementStrategy"]["cpu"],
            "gpu": json_data["placementStrategy"]["gpu"]
            }
    }

def build_department_schema_from_json(json_data, node_pools_map):
    return {
        "name": json_data["name"],
        "nodePoolsResources":  [build_node_pool_resources_from_json(node_pool_resource, node_pools_map=node_pools_map) for node_pool_resource in json_data["nodePoolsResources"]],
    }

def build_project_schema_from_json(json_data):
    return {
        "name": json_data["name"],
        "departmentId": int(json_data["departmentId"]),
        "clusterUuid": json_data["clusterUuid"],
        "defaultNodePools": json_data["defaultNodePools"] if json_data["defaultNodePools"] is not None else [],
        "permissions": {
        "users": json_data["permissions"]["users"] if json_data["permissions"]["users"] is not None else [],
        "groups": json_data["permissions"]["groups"] if json_data["permissions"]["groups"] is not None else [],
        "applications": []
        },
        "nodeAffinity": json_data["nodeAffinity"] if json_data["nodeAffinity"] is not None else [],
        "interactiveJobTimeLimitSecs": json_data["interactiveJobTimeLimitSecs"] if json_data["interactiveJobTimeLimitSecs"] is not None else [],
        "interactiveJobMaxIdleDurationSecs": json_data["interactiveJobMaxIdleDurationSecs"] if json_data["interactiveJobMaxIdleDurationSecs"] is not None else [],
        "interactivePreemptibleJobMaxIdleDurationSecs": json_data["interactivePreemptibleJobMaxIdleDurationSecs"] if json_data["interactivePreemptibleJobMaxIdleDurationSecs"] is not None else [],
        "trainingJobTimeLimitSecs": json_data["trainingJobTimeLimitSecs"] if json_data["trainingJobTimeLimitSecs"] is not None else [],
        "trainingJobMaxIdleDurationSecs": json_data["trainingJobMaxIdleDurationSecs"] if json_data["trainingJobMaxIdleDurationSecs"] is not None else [],
        "nodePoolsResources": json_data["nodePoolsResources"]
        
    }


if __name__ == "__main__":

    BASE_URL = "https://envinaclick.run.ai"
    CLIENT_ID="<APPLICATION_TOKEN_NAME>"
    CLIENT_SECRET = "<APPLICATION_SECRET"
    REALM = "envinaclick"

    old_cluster_2_8 = Cluster(
        base_url=BASE_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        realm=REALM,
        cluster_id="d96e8a65-7e6f-4c1f-92eb-ccd90d304fa4"
    )
    
    new_cluster_2_13 = Cluster(
        base_url=BASE_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        realm=REALM,
        cluster_id="fa3314fd-7351-4281-878f-99856735e941"
    )

    ###### 2.8 cluster ######
    token = old_cluster_2_8.generate_api_token()
    headers = {"authorization": f"Bearer {token}", 'content-type': "application/json"}

    ##### NodePools #####
    node_pools_map={}

    response = requests.get(f"{old_cluster_2_8.base_url}/v1/k8s/clusters/{old_cluster_2_8.cluster_id}/node-pools", headers=headers)
    response.raise_for_status()

    node_pools = response.json()
    # print(node_pools)
    for node_pool in node_pools:
        node_pool = build_node_pool_schema_from_json(node_pool)
        node_pools_map[node_pool["name"]] = node_pool["id"]

    ##### Departments #####
    old_departments_map={}

    response = requests.get(f"{old_cluster_2_8.base_url}/v1/k8s/clusters/{old_cluster_2_8.cluster_id}/departments", headers=headers)
    response.raise_for_status()
    
    departments = response.json()
    for department in departments:
        old_departments_map[department["name"]] = department["id"]
        build_department_schema_from_json(json_data=department, node_pools_map=node_pools_map)

    ##### Projects #####
    response = requests.get(f"{old_cluster_2_8.base_url}/v1/k8s/clusters/{old_cluster_2_8.cluster_id}/projects", headers=headers)
    response.raise_for_status()
    
    old_projects_map = {}
    projects = response.json()
    for project in projects:
        old_projects_map[project["id"]] = project["name"]


    ####################################################################################################
    ######################### 2.13 cluster #########################
    ####################################################################################################

    token = new_cluster_2_13.generate_api_token()
    headers = {"authorization": f"Bearer {token}", 'content-type': "application/json"}
    
    ######################### Node Pools #########################
    print('\n')
    print("######################### Node Pools #########################")
    print('\n')


    node_pools_list = [build_node_pool_schema_from_json(node_pool) for node_pool in node_pools]

    for node_pool in node_pools_list:
        if node_pool["name"] == "default":
            continue
        print(f"Creating node pool: {node_pool["name"]}...")
        response = requests.post(f"{new_cluster_2_13.base_url}/v1/k8s/clusters/{new_cluster_2_13.cluster_id}/node-pools", headers=headers, json=node_pool)
        
        if response.status_code == 409 and "already exists" in response.text:
            print(f"Skipping existing node pool {department["name"]}")
            continue
        elif response.status_code > 202:
            raise SystemExit(response.text)
        else:
            print(response.status_code)
        

    ######################### Departments #########################
    print('\n\n')
    print("######################### Departments #########################")
    print('\n')

    node_pools_map = {}
    response = requests.get(f"{new_cluster_2_13.base_url}/v1/k8s/clusters/{new_cluster_2_13.cluster_id}/node-pools", headers=headers)
    response.raise_for_status()
    node_pools = response.json()

    for node_pool in node_pools:
        node_pools_map[node_pool["name"]]=node_pool["id"]
    
    for department in departments:
        if department["name"] == "default":
            print(f"Skipping default department...")
            continue
        print(f"Creating department: {department["name"]}...")
        for i, node_pool_resource in enumerate(department["nodePoolsResources"]):
            # Change node_pool ID from 2.8 to the correct id in 2.13
            node_pool_resource["nodePool"]["id"] = node_pools_map[node_pool_resource["nodePool"]["name"]]
            # department = build_department_schema_from_json(department, node_pools_map=node_pools_map)
            node_pool_resource = build_node_pool_resources_from_json(node_pool_resource, node_pools_map=node_pools_map)
            department["nodePoolsResources"][i] = node_pool_resource
        response = requests.post(f"{new_cluster_2_13.base_url}/v1/k8s/clusters/{new_cluster_2_13.cluster_id}/departments", headers=headers, json=department)
        if response.status_code == 409 and "already exists" in response.text:
            print(f"Skipping existing department {department["name"]}")
            continue
        elif response.status_code > 202:
            raise SystemExit(response.text)
        else:
            print(response.status_code)


    ######################### Projects #########################
    print('\n\n')
    print("######################### Projects #########################")
    print('\n')

    old_departments_map_id_to_new_id = {}
    new_departments_map = {}
    response = requests.get(f"{new_cluster_2_13.base_url}/v1/k8s/clusters/{new_cluster_2_13.cluster_id}/departments", headers=headers)
    response.raise_for_status()
    departments = response.json()
    
    for department in departments:
        old_departments_map_id_to_new_id[old_departments_map[department["name"]]] = department["id"]
        new_departments_map[department["name"]] = department["id"]

    for project in projects:
        print(f"Creating project: {project["name"]}...")
        project["departmentId"] = old_departments_map_id_to_new_id[project["departmentId"]]
        for i, node_pool_resource in enumerate(project["nodePoolsResources"]):
            project_node_pool_resource_name = project["nodePoolsResources"][i]["nodePool"]["name"]
            project["nodePoolsResources"][i]["nodePool"]["id"] = node_pools_map[project_node_pool_resource_name]
        response = requests.post(f"{new_cluster_2_13.base_url}/v1/k8s/clusters/{new_cluster_2_13.cluster_id}/projects", headers=headers, json=project)
        if response.status_code == 409 and "already exists" in response.text:
            print(f"Skipping existing project {project["name"]}")
            continue
        elif response.status_code > 202:
            raise SystemExit(response.text)
        else:
            print(response.text)


    ######################### Access Rules #########################
    print('\n\n')
    print("######################### Access Rules #########################")
    print('\n')

    response = requests.get(f"{new_cluster_2_13.base_url}/api/v1/authorization/access-rules", headers=headers)
    response.raise_for_status()
    access_rules = response.json()
    access_rules = access_rules["accessRules"]
    
    # Prepare relevant maps
    new_projects_map = {}
    response = requests.get(f"{new_cluster_2_13.base_url}/v1/k8s/clusters/{new_cluster_2_13.cluster_id}/projects", headers=headers)
    response.raise_for_status()
    projects = response.json()
    for project in projects:
        new_projects_map[project["name"]] = project["id"]

    old_projects_id_to_new = {}
    for key, value in old_projects_map.items():
        old_projects_id_to_new[key] = new_projects_map[value]
    

    for access_rule in access_rules:
        # Skip any clusters that do not belong to 2.8 for now, or if clusterId empty
        if "clusterId" not in access_rule:
            continue
        if access_rule["clusterId"] != old_cluster_2_8.cluster_id:
            continue
        # Removing unused fields in post request
        del access_rule["roleName"]
        del access_rule["scopeName"]
        del access_rule["createdAt"]
        del access_rule["updatedAt"]
        del access_rule["createdBy"]
        del access_rule["id"]
        del access_rule["tenantId"]
        del access_rule["clusterId"]
        
        if access_rule["scopeType"] == "project":
            access_rule["scopeId"] = str(old_projects_id_to_new[int(access_rule["scopeId"])])
        elif access_rule["scopeType"] == "department":
            access_rule["scopeId"] = str(old_departments_map_id_to_new_id[int(access_rule["scopeId"])])
        elif access_rule["scopeType"] == "cluster":
            access_rule["scopeId"] = new_cluster_2_13.cluster_id

        print(f"Creating access rule {access_rule}...")
        response = requests.post(f"{new_cluster_2_13.base_url}/api/v1/authorization/access-rules", headers=headers, json=access_rule)
        if response.status_code == 409 and "already exists" in response.text:
            print(f"Skipping existing access rule {access_rule}")
            continue
        elif response.status_code > 202 and response.status_code < 409:
            print(response.text)
            raise SystemExit(response.text)
        else:
            print(response.text)