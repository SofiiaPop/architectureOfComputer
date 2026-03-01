package com.task.hazelcast;

import com.hazelcast.client.HazelcastClient;
import com.hazelcast.client.config.ClientConfig;
import com.hazelcast.core.HazelcastInstance;
import com.hazelcast.map.IMap;

public class DistributedMapDemo {

    public static void main(String[] args) throws InterruptedException, java.io.IOException {
        System.out.println("=== Task 3: Distributed Map Demo ===");

        ClientConfig clientConfig = new ClientConfig();
        clientConfig.setClusterName("dev");
        clientConfig.getNetworkConfig()
                .addAddress("localhost:5701", "localhost:5702", "localhost:5703");

        HazelcastInstance client = HazelcastClient.newHazelcastClient(clientConfig);
        System.out.println("Connected to Hazelcast cluster.");

        IMap<Integer, String> distributedMap = client.getMap("entries");

        System.out.println("Writing 1000 entries to distributed map 'entries'...");
        long start = System.currentTimeMillis();

        for (int i = 0; i <= 1000; i++) {
            distributedMap.put(i, "value-" + i);
        }

        long elapsed = System.currentTimeMillis() - start;
        System.out.printf("Done. Total entries in map: %d  (wrote in %d ms)%n",
                distributedMap.size(), elapsed);

        System.out.println("\n--- Map stats ---");
        System.out.println("Total size: " + distributedMap.size());
        System.out.println("\nOpen Management Center at http://localhost:8080 to see key distribution per node.");
        System.out.println("Press ENTER to shut down client...");
        System.in.read();

        client.shutdown();
        System.out.println("Client shut down.");
    }
}