#!/bin/bash
set -e

echo "Waiting for Neo4j to be ready..."
until cypher-shell -u ${NEO4J_USERNAME:-neo4j} -p ${NEO4J_PASSWORD:-sentinel_password} -a ${NEO4J_URI:-bolt://neo4j:7687} "RETURN 1" > /dev/null 2>&1; do
    sleep 2
done
echo "Neo4j is ready."

echo "Applying constraints and indexes..."
cypher-shell -u ${NEO4J_USERNAME:-neo4j} -p ${NEO4J_PASSWORD:-sentinel_password} -a ${NEO4J_URI:-bolt://neo4j:7687} -f constraints.cypher
echo "Constraints applied successfully."
