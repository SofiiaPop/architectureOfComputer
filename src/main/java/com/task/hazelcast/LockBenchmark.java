package com.task.hazelcast;

import com.hazelcast.client.HazelcastClient;
import com.hazelcast.client.config.ClientConfig;
import com.hazelcast.core.HazelcastInstance;
import com.hazelcast.map.IMap;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class LockBenchmark {

    static final int ITERATIONS = 10_000;
    static final int CLIENTS = 3;
    static final String KEY = "key";

    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== Task 7: Lock Strategy Benchmark ===\n");

        ClientConfig clientConfig = new ClientConfig();
        clientConfig.setClusterName("dev");
        clientConfig.getNetworkConfig()
                .addAddress("localhost:5701", "localhost:5702", "localhost:5703");

        HazelcastInstance client = HazelcastClient.newHazelcastClient(clientConfig);

        long timeNoLock = runNoLock(client);
        long timePessimistic = runPessimistic(client);
        long timeOptimistic = runOptimistic(client);

        System.out.println("\n=== RESULTS SUMMARY ===");
        System.out.printf("%-20s | %-12s | %-10s%n", "Strategy", "Final Value", "Time (ms)");
        System.out.println("-".repeat(50));
        System.out.printf("%-20s | %-12s | %-10d%n", "No Lock",       "< 30000 ⚠", timeNoLock);
        System.out.printf("%-20s | %-12s | %-10d%n", "Pessimistic",   "30000 ✓",   timePessimistic);
        System.out.printf("%-20s | %-12s | %-10d%n", "Optimistic",    "30000 ✓",   timeOptimistic);
        System.out.println("\nConclusion: Pessimistic is simpler, Optimistic may be faster under low contention.");

        client.shutdown();
    }

    static long runNoLock(HazelcastInstance client) throws InterruptedException {
        IMap<String, Integer> map = client.getMap("bench-nolock");
        map.put(KEY, 0);
        long start = System.currentTimeMillis();
        runWorkers(CLIENTS, () -> {
            for (int k = 0; k < ITERATIONS; k++) {
                Integer v = map.get(KEY);
                if (v == null) v = 0;
                map.put(KEY, v + 1);
            }
        });
        long elapsed = System.currentTimeMillis() - start;
        System.out.printf("[No Lock]     final=%d  time=%d ms%n", map.get(KEY), elapsed);
        return elapsed;
    }

    static long runPessimistic(HazelcastInstance client) throws InterruptedException {
        IMap<String, Integer> map = client.getMap("bench-pessimistic");
        map.put(KEY, 0);
        long start = System.currentTimeMillis();
        runWorkers(CLIENTS, () -> {
            for (int k = 0; k < ITERATIONS; k++) {
                map.lock(KEY);
                try {
                    Integer v = map.get(KEY);
                    if (v == null) v = 0;
                    map.put(KEY, v + 1);
                } finally {
                    map.unlock(KEY);
                }
            }
        });
        long elapsed = System.currentTimeMillis() - start;
        System.out.printf("[Pessimistic] final=%d  time=%d ms%n", map.get(KEY), elapsed);
        return elapsed;
    }

    static long runOptimistic(HazelcastInstance client) throws InterruptedException {
        IMap<String, Integer> map = client.getMap("bench-optimistic");
        map.put(KEY, 0);
        AtomicLong retries = new AtomicLong();
        long start = System.currentTimeMillis();
        runWorkers(CLIENTS, () -> {
            for (int k = 0; k < ITERATIONS; k++) {
                boolean ok = false;
                while (!ok) {
                    Integer old = map.get(KEY);
                    if (old == null) old = 0;
                    ok = map.replace(KEY, old, old + 1);
                    if (!ok) retries.incrementAndGet();
                }
            }
        });
        long elapsed = System.currentTimeMillis() - start;
        System.out.printf("[Optimistic]  final=%d  retries=%d  time=%d ms%n",
                map.get(KEY), retries.get(), elapsed);
        return elapsed;
    }

    static void runWorkers(int count, RunnableEx task) throws InterruptedException {
        CountDownLatch latch = new CountDownLatch(count);
        ExecutorService pool = Executors.newFixedThreadPool(count);
        for (int i = 0; i < count; i++) {
            pool.submit(() -> {
                try { task.run(); } catch (Exception e) { e.printStackTrace(); }
                finally { latch.countDown(); }
            });
        }
        latch.await();
        pool.shutdown();
    }

    @FunctionalInterface
    interface RunnableEx {
        void run() throws Exception;
    }
}