Restart product catalog service to get the most recent product list

```
# Option 1: Restart the pod (what you've been doing)
kubectl delete pod -l app=productcatalogservice

# Option 2: Send SIGUSR1 signal to reload catalog without restart
kubectl exec deployment/productcatalogservice -- kill -USR1 1

# Option 3: Scale down and up
kubectl scale deployment productcatalogservice --replicas=0
kubectl scale deployment productcatalogservice --replicas=1
```


```
k delete pod/<pod_id>
```


Deploy MCP Server to Cluster
```
cd /home/thong/Desktop/microservices-demo/src/mcpserver && docker build -t gcr.io/gke-hack-471804/mcpserver:latest .
```


```
docker push gcr.io/gke-hack-471804/mcpserver:latest
```

```shell
PGPASSWORD='Admin123' psql -h 10.103.0.3 -U postgres -c '\l'
```
                                                                List of databases
     Name      |       Owner       | Encoding |  Collate   |   Ctype    | ICU Locale | Locale Provider |            Access privileges            
---------------+-------------------+----------+------------+------------+------------+-----------------+-----------------------------------------
 carts         | cloudsqlsuperuser | UTF8     | en_US.UTF8 | en_US.UTF8 |            | libc            | 
 cloudsqladmin | cloudsqladmin     | UTF8     | en_US.UTF8 | en_US.UTF8 |            | libc            | 
 orders        | cloudsqlsuperuser | UTF8     | en_US.UTF8 | en_US.UTF8 |            | libc            | 
 postgres      | cloudsqlsuperuser | UTF8     | en_US.UTF8 | en_US.UTF8 |            | libc            | 
 products      | cloudsqlsuperuser | UTF8     | en_US.UTF8 | en_US.UTF8 |            | libc            | 
 template0     | cloudsqladmin     | UTF8     | en_US.UTF8 | en_US.UTF8 |            | libc            | =c/cloudsqladmin                       +
               |                   |          |            |            |            |                 | cloudsqladmin=CTc/cloudsqladmin
 template1     | cloudsqlsuperuser | UTF8     | en_US.UTF8 | en_US.UTF8 |            | libc            | =c/cloudsqlsuperuser                   +
               |                   |          |            |            |            |                 | cloudsqlsuperuser=CTc/cloudsqlsuperuser
(7 rows)

thong@alloydb-jumpbox:~$ 