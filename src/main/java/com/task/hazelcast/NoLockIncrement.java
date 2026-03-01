package com.task.hazelcast;

import com.hazelcast.client.HazelcastClient;
import com.hazelcast.client.config.ClientConfig;
import com.hazelcast.core.HazelcastInstance;
import com.hazelcast.map.IMap;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class NoLockIncrement {

    static final String MAP_NAME = "counter-map";
    static final String KEY = "key";
    static final int ITERATIONS = 10_000;
    static final int CLIENTS = 3;

    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== Task 4: No-Lock Increment (3 clients x 10K = expected 30K) ===");

        ClientConfig clientConfig = new ClientConfig();
        clientConfig.setClusterName("dev");
        clientConfig.getNetworkConfig()
                .addAddress("localhost:5701", "localhost:5702", "localhost:5703");

        HazelcastInstance client = HazelcastClient.newHazelcastClient(clientConfig);
        IMap<String, Integer> map = client.getMap(MAP_NAME);

        map.put(KEY, 0);
        System.out.println("Initial value: " + map.get(KEY));

        CountDownLatch latch = new CountDownLatch(CLIENTS);
        ExecutorService pool = Executors.newFixedThreadPool(CLIENTS);

        long start = System.currentTimeMillis();

        for (int c = 0; c < CLIENTS; c++) {
            final int clientId = c;
            pool.submit(() -> {
                try {
                    for (int k = 0; k < ITERATIONS; k++) {
                        map.putIfAbsent(KEY, 0);
                        Integer value = map.get(KEY);
                        value++;
                        map.put(KEY, value);
                    }
                    System.out.printf("Client %d finished%n", clientId);
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        pool.shutdown();

        long elapsed = System.currentTimeMillis() - start;
        int finalValue = map.get(KEY);

        System.out.printf("%nFinal value (NO LOCK): %d  (expected 30000, lost %d updates)%n",
                finalValue, 30_000 - finalValue);
        System.out.printf("Time elapsed: %d ms%n", elapsed);

        client.shutdown();
    }
}