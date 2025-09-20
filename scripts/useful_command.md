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
gcloud compute ssh alloydb-jumpbox --zone=us-central1-a
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


```
docker build -t reviewservice .
docker tag reviewservice gcr.io/gke-hack-471804/reviewservice:latest
docker push gcr.io/gke-hack-471804/reviewservice:latest
```



```
echo "🔄 RESTARTING FRONTEND..."
pkill -f "./frontend" 2>/dev/null || true
sleep 2

export PRODUCT_CATALOG_SERVICE_ADDR="localhost:3550" \
CURRENCY_SERVICE_ADDR="localhost:7000" \
CART_SERVICE_ADDR="localhost:7070" \
RECOMMENDATION_SERVICE_ADDR="localhost:8081" \
CHECKOUT_SERVICE_ADDR="localhost:5050" \
SHIPPING_SERVICE_ADDR="localhost:50051" \
AD_SERVICE_ADDR="localhost:9555" \
SHOPPING_ASSISTANT_SERVICE_ADDR="localhost:8085" \
REVIEW_SERVICE_ADDR="localhost:8082" \
COLLECTOR_SERVICE_ADDR="localhost:4317" && ./frontend > frontend.log 2>&1 &

echo "Frontend restarted! PID: $!"
sleep 3

echo "✅ Checking if frontend is responding..."
curl -s -w "%{http_code}\n" http://localhost:8080/ | tail -1
```


```shell
kubectl describe pod -l app=productcatalogservice | grep "Image:" -A1 -B1

kubectl rollout restart deployment/productcatalogservice 

kubectl rollout status deployment/productcatalogservice

kubectl delete pod -l app=productcatalogservice

kubectl get pods -l app=productcatalogservice -w
```

```
gcloud container images add-tag gcr.io/gke-hack-471804/productcatalogservice@sha256:66e2a90b604f7010ca3565a5c827365a9ea0f4d2ba70e2565aaedb930894a986 gcr.io/gke-hack-471804/productcatalogservice:latest
```