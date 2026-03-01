package com.task.hazelcast;

import com.hazelcast.client.HazelcastClient;
import com.hazelcast.client.config.ClientConfig;
import com.hazelcast.collection.IQueue;
import com.hazelcast.core.HazelcastInstance;

import java.util.concurrent.TimeUnit;

public class QueueFullDemo {

    static final String QUEUE_NAME = "bounded-queue";

    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== Task 8b: Queue Full Behavior (No Consumers) ===");
        System.out.println("Demonstrating what happens when producer writes to a full bounded queue");

        ClientConfig clientConfig = new ClientConfig();
        clientConfig.setClusterName("dev");
        clientConfig.getNetworkConfig()
                .addAddress("localhost:5701", "localhost:5702", "localhost:5703");

        HazelcastInstance client = HazelcastClient.newHazelcastClient(clientConfig);
        IQueue<Integer> queue = client.getQueue(QUEUE_NAME);
        queue.clear();

        System.out.println("Writing to bounded queue (max=10) with NO consumers...\n");

        for (int i = 1; i <= 15; i++) {
            System.out.printf("[Producer] Trying to offer value %d | current size=%d%n", i, queue.size());
            // offer() with 3s timeout - returns false immediately if queue is full after timeout
            boolean offered = queue.offer(i, 3, TimeUnit.SECONDS);
            if (offered) {
                System.out.printf("  => Accepted. Queue size now: %d%n", queue.size());
            } else {
                System.out.printf("  => BLOCKED for 3s then REJECTED! Queue is FULL (size=%d). Value %d NOT enqueued.%n",
                        queue.size(), i);
                System.out.println("  => With queue.put() the producer would block INDEFINITELY until space is available.");
            }
        }

        System.out.println("\n=== OBSERVATION ===");
        System.out.println("Final queue size: " + queue.size());
        System.out.println("- offer(value, timeout, unit): waits up to timeout, returns false if still full");
        System.out.println("- put(value):                  blocks indefinitely until space is available");
        System.out.println("- offer(value):                returns false immediately if queue is full (no wait)");

        client.shutdown();
    }
}