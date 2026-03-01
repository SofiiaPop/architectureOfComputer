package com.task.hazelcast;

import com.hazelcast.client.HazelcastClient;
import com.hazelcast.client.config.ClientConfig;
import com.hazelcast.collection.IQueue;
import com.hazelcast.core.HazelcastInstance;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class BoundedQueueDemo {

    static final String QUEUE_NAME = "bounded-queue";
    static final int PRODUCE_COUNT = 100;

    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== Task 8: Bounded Queue Demo ===");
        System.out.println("Queue max size: 10 (configured server-side) | Producer: 1..100 | Consumers: 2");

        ClientConfig clientConfig = new ClientConfig();
        clientConfig.setClusterName("dev");
        clientConfig.getNetworkConfig()
                .addAddress("localhost:5701", "localhost:5702", "localhost:5703");

        HazelcastInstance client = HazelcastClient.newHazelcastClient(clientConfig);
        IQueue<Integer> queue = client.getQueue(QUEUE_NAME);
        queue.clear();

        AtomicInteger consumer1Count = new AtomicInteger(0);
        AtomicInteger consumer2Count = new AtomicInteger(0);
        CountDownLatch consumersReady = new CountDownLatch(2);
        CountDownLatch consumersDone = new CountDownLatch(2);

        ExecutorService pool = Executors.newFixedThreadPool(3);

        pool.submit(() -> {
            consumersReady.countDown();
            try {
                while (true) {
                    Integer value = queue.poll(5, TimeUnit.SECONDS);
                    if (value == null || value == -1) {
                        System.out.println("[Consumer-1] Received stop signal or timeout. Total: " + consumer1Count.get());
                        break;
                    }
                    System.out.println("[Consumer-1] Read: " + value);
                    consumer1Count.incrementAndGet();
                    Thread.sleep(50);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                consumersDone.countDown();
            }
        });

        pool.submit(() -> {
            consumersReady.countDown();
            try {
                while (true) {
                    Integer value = queue.poll(5, TimeUnit.SECONDS);
                    if (value == null || value == -1) {
                        System.out.println("[Consumer-2] Received stop signal or timeout. Total: " + consumer2Count.get());
                        break;
                    }
                    System.out.println("[Consumer-2] Read: " + value);
                    consumer2Count.incrementAndGet();
                    Thread.sleep(50);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                consumersDone.countDown();
            }
        });

        consumersReady.await();
        System.out.println("Both consumers ready. Starting producer...\n");

        pool.submit(() -> {
            try {
                for (int i = 1; i <= PRODUCE_COUNT; i++) {
                    System.out.printf("[Producer] Offering value %d | Queue size before: %d%n", i, queue.size());
                    boolean offered = queue.offer(i, 10, TimeUnit.SECONDS);
                    if (offered) {
                        System.out.printf("[Producer] Sent: %d | Queue size after: %d%n", i, queue.size());
                    } else {
                        System.out.printf("[Producer] TIMEOUT - could not enqueue %d (queue full!)%n", i);
                    }
                    Thread.sleep(20);
                }
                queue.put(-1);
                queue.put(-1);
                System.out.println("[Producer] Done. Sent 2 poison pills to stop consumers.");
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });

        consumersDone.await();
        pool.shutdown();

        System.out.printf("%n=== SUMMARY ===%n");
        System.out.printf("Consumer-1 received: %d messages%n", consumer1Count.get());
        System.out.printf("Consumer-2 received: %d messages%n", consumer2Count.get());
        System.out.printf("Total consumed:      %d / %d%n",
                consumer1Count.get() + consumer2Count.get(), PRODUCE_COUNT);
        System.out.println("Note: Each message consumed by exactly ONE consumer (competing consumers pattern).");
        System.out.println("Note: Queue was bounded to 10 - producer blocked when queue was full until consumer freed space.");

        client.shutdown();
    }
}