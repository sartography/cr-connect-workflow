#psql -h localhost -U postgres -d postgres
#psql -h localhost -U crc_user -d crc_test
#psql -h localhost -U crc_user -d crc_dev
docker exec -it postgres-db-1 psql -U crc_user crc_dev
