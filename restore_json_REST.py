import sys
import os
import json
import requests
import logging
import argparse
import pprint
from dataclasses import dataclass

@dataclass
class Cluster:
    base_url: str
    client_id: str
    client_secret: str
    cluster_id: str

    def generate_api_token(self):
        payload = {"grantType": "app_token", "AppId": self.client_id, "AppSecret": self.client_secret}
        headers = {'content-type': "application/json"}
        url = f"{self.base_url}/api/v1/token"
        try:
            response = requests.post(url=url, json=payload, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            if "accessToken" not in response_json:
                raise SystemExit(f"failed to get access token from response. response body={response_json}")

            return response_json["accessToken"]

        except requests.exceptions.HTTPError as err:
            print(f"failed to get api token. err={err} \n message={err.response.text}" )
            raise SystemExit(err)
        except requests.exceptions.JSONDecodeError as err:
            print(f"failed to decode json response. err={err}")
            raise SystemExit(err)


def build_node_pool_resources_from_json(json_data, node_pools_map):
    return             {
                "nodePool": {
                    "name": json_data["nodePool"]["name"],
                    "id": f"{node_pools_map[json_data["nodePool"]["name"]]}",
                },
                "gpu": {
                    "deserved": json_data["gpu"]["deserved"],
                    "limit": json_data["gpu"]["maxAllowed"],
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

def restore_json_from_file(file_name):
    try:
        with open(file_name, "r", encoding='utf-8') as file:
            return json.load(file)
    except json.decoder.JSONDecodeError as err:
        print(f"error retrieving json from {file_name}: {err}")
        return None
    
#Used to retrieve environment, compute, and datasource asset ids for creating templates
def get_id_by_name(apiEndpoint,resourceName):
        response = requests.get(f"{cluster.base_url}/{apiEndpoint}", headers=headers, params=f"name={resourceName}")
        response.raise_for_status()
        return response.json()["entries"][0]["meta"]["id"]

def get_api_endpoint_for_resource(resourceType,kind):
    return f"/api/v1/asset/{resourceType}/{camel_to_hyphen(kind)}"

def camel_to_hyphen(s):
    result = []
    for c in s:
        if c.isupper():
            result.extend(['-', c.lower()])
        else:
            result.append(c)
    return ''.join(result)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Import Runai resources into a new cluster from json files")

    # Add arguments
    parser.add_argument('-url','--base_url', type=str, help='Base url of the cluster (e.g. https://test.run.ai)')
    parser.add_argument('-i','--client_id', type=str, help='Client ID of the application you created in the Runai UI')
    parser.add_argument('-s','--client_secret', type=str, help='Client Secret of the application you created in the Runai UI')
    parser.add_argument('-c','--cluster_id', type=str, help='Cluster ID for the new Runai cluster')
    parser.add_argument('-l', '--log_level', type=str, help="Log level (INFO,WARN,DEBUG,etc)", default="INFO")
    parser.add_argument('--convert_new_pvc_datasources_to_existing', action="store_true", help="Convert any PVC datasources that created a new PVC to use an existing PVC instead." \
                        "Assumes you have already transferred over or created the PVCs in the new cluster with the same claim name as in the original cluster", default=False)

    args=parser.parse_args()

    cluster = Cluster(
        base_url=args.base_url,
        client_id=args.client_id,
        client_secret=args.client_secret,
        cluster_id=args.cluster_id
    )

    logging.basicConfig(level=args.log_level, format='%(levelname)s: %(message)s\n')
    if args.log_level=="DEBUG":
        logging.getLogger("urllib3").setLevel("WARNING")   #Set Requests level to warning to avoid clogging logs with useless messages

    token = cluster.generate_api_token()
    headers = {"authorization": f"Bearer {token}", 'content-type': "application/json"}
    directory_name="2.16_cluster_json"
    
    ##### NodePools #####
    node_pools_map={}

    node_pools = restore_json_from_file(f"{directory_name}/node_pool.json")
    # print(node_pools)
    for node_pool in node_pools:
        node_pool = build_node_pool_schema_from_json(node_pool)
        node_pools_map[node_pool["name"]] = node_pool["id"]

    ##### Departments #####
    old_departments_map={}

    departments = restore_json_from_file(f"{directory_name}/department.json")
    for department in departments:
        old_departments_map[department["name"]] = department["id"]
        build_department_schema_from_json(json_data=department, node_pools_map=node_pools_map)

    ##### Projects #####
    old_projects_map = {}
    projects = restore_json_from_file(f"{directory_name}/project.json")
    for project in projects:
        old_projects_map[project["id"]] = project["name"]

    ##### Node Types #####
    old_nodetypes_map = {}
    nodetypes = restore_json_from_file(f"{directory_name}/nodetypes.json")
    for nodetype in nodetypes:
        old_nodetypes_map[nodetype["name"]] = nodetype["id"]
    
    
    ######################### Node Pools #########################
    print('\n')
    logging.info("######################### Node Pools #########################")



    node_pools_list = [build_node_pool_schema_from_json(node_pool) for node_pool in node_pools]

    for node_pool in node_pools_list:
        try:
            if node_pool["name"] == "default":
                continue
            logging.info(f"Creating node pool: {node_pool["name"]}...")
            response = requests.post(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/node-pools", headers=headers, json=node_pool)
            
            if response.status_code == 409 and "already exists" in response.text:
                logging.info(f"Skipping existing node pool {node_pool["name"]}")
                continue
            elif response.status_code > 202:
                logging.info(f"Failed to create nodepool {node_pool["name"]} due to {e}")
                logging.debug(f"Json sent was {pprint.pformat(node_pool)}")
                raise SystemExit(response.text)
            else:
                logging.info(response.status_code)
        except Exception as e:
            logging.info(f"Failed to create nodepool {node_pool["name"]} due to {e}")
            logging.debug(f"Json sent was {pprint.pformat(node_pool)}")

    ######################### Departments #########################
    print('\n\n')
    logging.info("######################### Departments #########################")
    print('\n')

    node_pools_map = {}
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/node-pools", headers=headers)
    response.raise_for_status()
    node_pools = response.json()

    for node_pool in node_pools:
        node_pools_map[node_pool["name"]]=node_pool["id"]
    
    for department in departments:
        try:
            if department["name"] == "default":
                logging.info(f"Skipping default department...")
                continue
            logging.info(f"Creating department: {department["name"]}...")
            for i, node_pool_resource in enumerate(department["nodePoolsResources"]):
                # Change node_pool ID from 2.16 to the correct id in 2.18
                node_pool_resource["nodePool"]["id"] = node_pools_map[node_pool_resource["nodePool"]["name"]]
                # department = build_department_schema_from_json(department, node_pools_map=node_pools_map)
                node_pool_resource = build_node_pool_resources_from_json(node_pool_resource, node_pools_map=node_pools_map)
                department["nodePoolsResources"][i] = node_pool_resource
            new_department_json={}
            new_department_json["name"]=department["name"]
            new_department_json["clusterId"]=cluster.cluster_id
            new_department_json["resources"]=department["nodePoolsResources"]
            response = requests.post(f"{cluster.base_url}/api/v1/org-unit/departments", headers=headers, json=new_department_json)
            if response.status_code == 409 and "already exists" in response.text:
                logging.info(f"Skipping existing department {department["name"]}")
                continue
            elif response.status_code > 202:
                logging.info(f"Failed to create department {department["name"]}")
                logging.debug(f"Json sent was {pprint.pformat(department)}")
                raise SystemExit(response.text)
            else:
                logging.info(response.status_code)
        except Exception as e:
            logging.info(f"Failed to create department {department["name"]} due to {e}")
            logging.debug(f"Json sent was {pprint.pformat(department)}")


    ######################### Projects #########################
    print('\n\n')
    logging.info("######################### Projects #########################")
    print('\n')

    old_departments_map_id_to_new_id = {}
    new_departments_map = {}
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/departments", headers=headers)
    response.raise_for_status()
    departments = response.json()
    
    for department in departments:
        old_departments_map_id_to_new_id[old_departments_map[department["name"]]] = department["id"]
        new_departments_map[department["name"]] = department["id"]

    old_nodetypes_map_id_to_new_id = {}
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/nodetypes", headers=headers)
    response.raise_for_status()
    nodetypes = response.json()
    
    for nodetype in nodetypes:
        old_nodetypes_map_id_to_new_id[old_nodetypes_map[nodetype["name"]]] = nodetype["id"]


    for project in projects:
        try:
            logging.info(f"Creating project: {project["name"]}")
            project["departmentId"] = old_departments_map_id_to_new_id[project["departmentId"]]
            for i, node_pool_resource in enumerate(project["nodePoolsResources"]):
                project_node_pool_resource_name = project["nodePoolsResources"][i]["nodePool"]["name"]
                project["nodePoolsResources"][i]["nodePool"]["id"] = node_pools_map[project_node_pool_resource_name]
            for workloadType in project["nodeAffinity"]:
                for i, nodeType in enumerate(project["nodeAffinity"][workloadType]["selectedTypes"]):
                    oldNodeTypeId=project["nodeAffinity"][workloadType]["selectedTypes"][i]["id"]
                    project["nodeAffinity"][workloadType]["selectedTypes"][i]["id"]=old_nodetypes_map_id_to_new_id[oldNodeTypeId]
            response = requests.post(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/projects", headers=headers, json=project)
            if response.status_code == 409 and "already exists" in response.text:
                logging.info(f"Skipping existing project {project["name"]}")
                continue
            elif response.status_code > 202:
                logging.info(f"Failed to create project {project["name"]}")
                logging.debug(f"Json sent was {pprint.pformat(project)}")
                raise SystemExit(response.text)
            else:
                logging.info(response.text)
        except Exception as e:
            logging.info(f"Failed to create project {project["name"]} due to {e}")
            logging.debug(f"Json sent was {pprint.pformat(project)}")


    ######################### Access Rules #########################
    print('\n\n')
    logging.info("######################### Access Rules #########################")
    print('\n')

    access_rules_json=restore_json_from_file(f"{directory_name}/access_rule.json")
    access_rules = access_rules_json["accessRules"]
    
    # Prepare relevant maps
    new_projects_map = {}
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/projects", headers=headers)
    response.raise_for_status()
    projects = response.json()
    for project in projects:
        new_projects_map[project["name"]] = project["id"]

    old_projects_id_to_new = {}
    for key, value in old_projects_map.items():
        old_projects_id_to_new[key] = new_projects_map[value]
    
    for access_rule in access_rules:
        # Skip any clusters that do not belong to 2.16 for now, or if clusterId empty
        # if "clusterId" not in access_rule:
        #     continue
        # if access_rule["clusterId"] != old_cluster_cluster_id:
        #     continue

        #Store old roleName and scopeName for logging purposes
        oldRoleName=access_rule["roleName"]
        oldScopeName=access_rule["scopeName"]
        # Removing unused fields in post request
        for key in ["roleName","scopeName","createdAt","updatedAt","createdBy","id","tenantId","clusterId"]:
            try:
                del access_rule[key]
            except KeyError as err:
                continue
        
        if access_rule["scopeType"] == "project":
            access_rule["scopeId"] = str(old_projects_id_to_new[int(access_rule["scopeId"])])
        elif access_rule["scopeType"] == "department":
            access_rule["scopeId"] = str(old_departments_map_id_to_new_id[int(access_rule["scopeId"])])
        elif access_rule["scopeType"] == "cluster":
            access_rule["scopeId"] = cluster.cluster_id

        logging.info(f"Creating access rule for user {access_rule["subjectId"]} and role {oldRoleName} with scope {oldScopeName}")
        try:
            response = requests.post(f"{cluster.base_url}/api/v1/authorization/access-rules", headers=headers, json=access_rule)
            if response.status_code == 409 and "already exists" in response.text:
                logging.info(f"Skipping existing access rule {access_rule["name"]}")
                continue
            elif response.status_code > 202 and response.status_code < 409:
                logging.info(response.text)
                logging.info(f"Failed to create access rule for user {access_rule["subjectId"]} and role {oldRoleName} with scope {oldScopeName} due to {e}")
                logging.debug(f"Json sent was {pprint.pformat(access_rule)}")
                raise SystemExit(response.text)
            else:
                logging.info(response.text)
        except Exception as e:
            logging.info(f"Failed to create access rule for user {access_rule["subjectId"]} and role {oldRoleName} with scope {oldScopeName} due to {e}")
            logging.debug(f"Json sent was {pprint.pformat(access_rule)}")

    resourceDb={}
    resourceOldIdToNewIdDb={}


    ######################### Environment,Compute,Datasource,Workload Template #########################
    for resourceType in ["environment","compute","credentials","datasource","workload-template"]:
        print('\n\n')
        logging.info(f"######################### {resourceType}s #########################")
        print('\n')
        resourceType_json=restore_json_from_file(f"{directory_name}/{resourceType}.json")
        resources = resourceType_json["entries"]
        resourceDb[resourceType]={}
        resourceOldIdToNewIdDb[resourceType]={}

        for entry in resources:
            # Removing unused fields in post request
            meta=entry["meta"]
            oldId=meta["id"]
            #Set apiEndpoint before removing "kind" from "meta" block - necessary for credentials and datasources
            apiEndpoint=f"api/v1/asset/{resourceType}"
            if resourceType in ["credentials","datasource"]:
                resourceKind=meta["kind"]
                apiEndpoint=get_api_endpoint_for_resource(resourceType,resourceKind)
            for key in ["createdAt","updatedAt","updatedBy","createdBy","id","tenantId","clusterId", "kind","projectName"]:
                try:
                    del meta[key]
                except KeyError as err:
                    continue
            if meta["scope"] == "project":
                meta["projectId"] = old_projects_id_to_new[int(meta["projectId"])]
            elif meta["scope"] == "department":
                meta["departmentId"] = str(old_departments_map_id_to_new_id[int(meta["departmentId"])])
            elif meta["scope"] == "cluster":
                meta["clusterId"] = cluster.cluster_id

            if resourceType=="compute":
                #clean up spec fields based on other fields
                spec=entry["spec"]
                if spec["gpuDevicesRequest"]!=1:
                    try:
                        del spec["gpuRequestType"]
                    except KeyError:    #Sometimes compute profiles with 0 gpu requests have this field, sometimes they don't. Not sure what makes a difference
                        pass
                      
            if resourceType=="credentials":
                    #.spec.existingSecretName must be set (if it's not already) for this credential to be useful, as otherwise some or all of the data is obfuscated when retrieved from the API. Secrets must be moved manually before or after this script is run.
                    if "existingSecretName" not in entry["spec"][resourceKind]:
                        entry["spec"]["existingSecretName"]=f"{resourceKind.lower()}-{meta["name"]}"   #Auto-generated secrets are named in the format {resourceKind (lowercased)}-{resourceName} e.g. accesskey-runai-wide for an AccessKey credential named runai-wide
                    else:
                        entry["spec"]["existingSecretName"]=entry["spec"][resourceKind]["existingSecretName"]
                    for key in list(entry["spec"].keys()):   #When creating from an existing secret, the only field that should be in spec is existingSecretName
                        if key!="existingSecretName": 
                            del entry["spec"][key]

            if resourceType=="datasource":
                #move all entries under resourceKind to directly under spec and then remove resourceKind
                for field in entry["spec"][resourceKind]:
                    entry["spec"][field]=entry["spec"][resourceKind][field]
                del entry["spec"][resourceKind]
                if resourceKind=="pvc":
                    if args.convert_new_pvc_datasources_to_existing:    
                        entry["spec"]["existingPvc"]=True
                    if "claimInfo" in entry["spec"] and  entry["spec"]["existingPvc"]:    #Don't want to specify claimInfo when the DS references an existing PVC - should only occur when --convert_new_pvc_datasources_to_existing is true
                        del entry["spec"]["claimInfo"]
                if resourceKind=="s3":  #For any datasources that reference credentials, convert the asset's id in the old cluster to the new cluster
                    entry["spec"]["accessKeyAssetId"]=resourceOldIdToNewIdDb["credentials"]["accessKey"][entry["spec"]["accessKeyAssetId"]]
                if resourceKind=="git":  #For any datasources that reference credentials, convert the asset's id in the old cluster to the new cluster
                    entry["spec"]["passwordAssetId"]=resourceOldIdToNewIdDb["credentials"]["password"][entry["spec"]["passwordAssetId"]]

            if resourceType=="workload-template":
                #Get ids of created assets to set in template json
                assets=entry["spec"]["assets"]
                try:
                    assets["environment"]=get_id_by_name(f"/api/v1/asset/environment",assets["environment"]["name"])
                except KeyError as err:
                    pass
                try:
                    assets["compute"]=get_id_by_name(f"/api/v1/asset/compute",assets["compute"]["name"])
                except KeyError as err:
                    pass
                try:
                    for datasource in assets["datasources"]:
                        datasource["id"]=get_id_by_name(get_api_endpoint_for_resource("datasource",datasource["kind"]),datasource["name"])
                        #Remove datasource name field since it's not in template API spec
                        del datasource["name"]
                except KeyError as err:
                    pass
                #TO-DO: Remove these lines once issues with workloadSupportedTypes field are resolved
                try:
                    del entry["meta"]["workloadSupportedTypes"] #API spec says this is supported, but when I try to submit with it set, it's rejected as an invalid field
                    del entry["spec"]["assets"]["workloadVolumes"]  #API spec just says this field is an "Array of Strings" - no idea what the format should be for it
                except KeyError as err:
                    pass

            


            logging.info(f"Creating {resourceType} {meta["name"]} using {apiEndpoint}: {entry}...\n")
            try:
                response = requests.post(f"{cluster.base_url}/{apiEndpoint}", headers=headers, json=entry)
                if response.status_code == 409 and "already exists" in response.text:
                    logging.info(f"{resourceType} {meta["name"]} already exists, retrieving it instead\n")
                    getListResponse=requests.get(f"{cluster.base_url}/{apiEndpoint}?name={meta["name"]}", headers=headers)  #Get list of resources and filter by resource name
                    listJson=getListResponse.json()
                    newId=listJson["entries"][0]["meta"]["id"]
                    getResourceResponse=requests.get(f"{cluster.base_url}/{apiEndpoint}/{newId}", headers=headers)
                    responseJson=getResourceResponse.json()
                elif response.status_code > 202 and response.status_code < 409:
                    logging.info(response.text)
                    logging.info(f"Failed to create {resourceType} {meta["name"]}")
                    logging.debug(f"Json sent was {pprint.pformat(entry)}")
                    raise SystemExit(response.text)
                else:
                    logging.info(response.text)
                    responseJson=response.json()
                #Add id of newly created resource to resource DB. Structure is [resourceType][optional datasource kind][resource id]=json. E.G. [environment: [001: json, 002: json], datasource: [pvc: [001: json], git: [001: json]]] etc
                if resourceType in ["credentials","datasource"]:
                    if resourceKind not in resourceDb[resourceType]:
                        resourceDb[resourceType][resourceKind]={} #Have to create dictionary for resourceKind before setting value inside it
                    resourceDb[resourceType][resourceKind][responseJson["meta"]["id"]]=responseJson
                else:
                    resourceDb[resourceType][responseJson["meta"]["id"]]=responseJson
                #Also add mapping of old id to new
                if resourceType in ["credentials","datasource"]:
                    if resourceKind not in resourceOldIdToNewIdDb[resourceType]:
                        resourceOldIdToNewIdDb[resourceType][resourceKind]={} #Have to create dictionary for resourceKind before setting value inside it
                    resourceOldIdToNewIdDb[resourceType][resourceKind][oldId]=responseJson["meta"]["id"]
                else:
                    resourceOldIdToNewIdDb[resourceType][oldId]=responseJson["meta"]["id"]
            except Exception as e:
                logging.info(f"Failed to create {resourceType} {meta["name"]} due to {e}")
                logging.debug(f"Json sent was {pprint.pformat(entry)}")


    # ######################### Workloads #########################
    # print('\n\n')
    # print("######################### Interactive Workloads #########################")
    # print('\n')

    # iws_json=restore_json_from_file(f"{directory_name}/iw.json")
    # iws = iws_json["entries"]
    # apiEndpoint='/api/v1/workloads/workspaces'

    # for iw in iws:
    #     newIwJson={}
    #     meta=iw["meta"]
    #     iwName=iw["meta"]["name"]
    #     oldIwId=iw["meta"]["id"]
    #     newIwJson["name"]=iwName
    #     newIwJson["useGivenNameAsPrefix"]=True
    #     newIwJson["projectId"]=str(old_projects_id_to_new[iw["meta"]["projectId"]])
    #     newIwJson["clusterId"]=cluster.cluster_id
    #     newIwJson["spec"]={}
    #     #Environment values
    #     #Get values of environment in new cluster based on old id
    #     newEnv=resourceDb["environment"][resourceOldIdToNewIdDb["environment"][iw["spec"]["assets"]["environment"]["id"]]]
    #     for value in "command", "args", "image", "imagePullPolicy", "workingDir", "createHomeDir", "probes", "nodePools", "environmentVariables", "annotations", "labels", "terminateAfterPreemption", "autoDeletionTimeAfterCompletionSeconds", "backoffLimit", "ports":
    #         if value in ["command", "args", "nodePools", "environmentVariables", "annotations", "labels", "terminateAfterPreemption", "autoDeletionTimeAfterCompletionSeconds", "backoffLimit", "ports"]:   #These values can be overwritten per workload
    #             try:
    #                 newIwJson["spec"][value]=iw["spec"]["specificEnv"][value]
    #             except KeyError:
    #                 logging.debug(f"Specific environment value {value} not set for workspace {iwName}, falling back to value in environment {iw["spec"]["assets"]["environment"]["name"]}")
    #         else:
    #             try:
    #                 newIwJson["spec"][value]=newEnv["spec"][value]
    #             except KeyError:
    #                 logging.info(f"Unable to find value {value} for workspace {iwName}, leaving blank")
    #     for value in "uidGidSource", "capabilities", "seccompProfileType", "runAsNonRoot", "readOnlyRootFilesystem", "runAsUid", "runAsGid", "supplementalGroups", "allowPrivilegeEscalation", "hostIpc", "hostNetwork":
    #         try:
    #             newIwJson["spec"]["security"][value]=newEnv["spec"][value]
    #         except KeyError:
    #             logging.info(f"Unable to find value {value} for workspace {iwName}, leaving blank")
    #     #Compute Values
    #     newCompute=resourceDb["compute"][resourceOldIdToNewIdDb["compute"][iw["spec"]["assets"]["compute"]["id"]]]
    #     newIwJson["spec"]["compute"]=newCompute["spec"]
    #     #Storage Values
    #     newStorages={}
    #     newIwJson["spec"]["storage"]={}
    #     for storage in iw["spec"]["assets"]["datasources"]:
    #         oldStorageId=storage["id"]
    #         newStorages[resourceOldIdToNewIdDb["datasource"][storage["kind"]][oldStorageId]]=resourceDb["datasource"][storage["kind"]][resourceOldIdToNewIdDb["datasource"][storage["kind"]][oldStorageId]]
    #         newStorageInstance=newStorages[resourceOldIdToNewIdDb["datasource"][storage["kind"]][oldStorageId]]["spec"]
    #         newStorageInstance["name"]=newStorages[resourceOldIdToNewIdDb["datasource"][storage["kind"]][oldStorageId]]["meta"]["name"]   #Extract name from meta block to spec block
    #         if storage["kind"] not in newIwJson["spec"]["storage"]:
    #             newIwJson["spec"]["storage"][storage["kind"]]=[]    #Have to create list before we can append to it, if it doesn't already exist
    #         newIwJson["spec"]["storage"][storage["kind"]].append(newStorageInstance)


    #     print(f"Creating Workspace {meta["name"]} using {apiEndpoint}: {entry}...\n")
    #     response = requests.post(f"{cluster.base_url}/{apiEndpoint}", headers=headers, json=newIwJson)
    #     if response.status_code == 409 and "already exists" in response.text:
    #         print(f"{resourceType} {meta["name"]} already exists\n")
    #     elif response.status_code > 202 and response.status_code < 409:
    #         print(response.text)
    #         raise SystemExit(response.text)
    #     else:
    #         print(response.text)