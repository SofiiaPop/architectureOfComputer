package com.task.hazelcast;

import com.hazelcast.client.HazelcastClient;
import com.hazelcast.client.config.ClientConfig;
import com.hazelcast.core.HazelcastInstance;
import com.hazelcast.map.IMap;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class OptimisticLockIncrement {

    static final String MAP_NAME = "counter-optimistic";
    static final String KEY = "key";
    static final int ITERATIONS = 10_000;
    static final int CLIENTS = 3;

    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== Task 6: Optimistic Lock Increment (3 clients x 10K = expected 30K) ===");

        ClientConfig clientConfig = new ClientConfig();
        clientConfig.setClusterName("dev");
        clientConfig.getNetworkConfig()
                .addAddress("localhost:5701", "localhost:5702", "localhost:5703");

        HazelcastInstance client = HazelcastClient.newHazelcastClient(clientConfig);
        IMap<String, Integer> map = client.getMap(MAP_NAME);

        // Reset
        map.put(KEY, 0);
        System.out.println("Initial value: " + map.get(KEY));

        CountDownLatch latch = new CountDownLatch(CLIENTS);
        ExecutorService pool = Executors.newFixedThreadPool(CLIENTS);
        AtomicLong totalRetries = new AtomicLong(0);

        long start = System.currentTimeMillis();

        for (int c = 0; c < CLIENTS; c++) {
            final int clientId = c;
            pool.submit(() -> {
                long retries = 0;
                try {
                    for (int k = 0; k < ITERATIONS; k++) {
                        boolean success = false;
                        while (!success) {
                            Integer oldValue = map.get(KEY);
                            if (oldValue == null) oldValue = 0;
                            Integer newValue = oldValue + 1;
                            success = map.replace(KEY, oldValue, newValue);
                            if (!success) retries++;
                        }
                    }
                    System.out.printf("Client %d finished (retries: %d)%n", clientId, retries);
                    totalRetries.addAndGet(retries);
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        pool.shutdown();

        long elapsed = System.currentTimeMillis() - start;
        int finalValue = map.get(KEY);

        System.out.printf("%nFinal value (OPTIMISTIC): %d  (expected 30000, lost %d updates)%n",
                finalValue, 30_000 - finalValue);
        System.out.printf("Total CAS retries: %d%n", totalRetries.get());
        System.out.printf("Time elapsed: %d ms%n", elapsed);

        client.shutdown();
    }
}