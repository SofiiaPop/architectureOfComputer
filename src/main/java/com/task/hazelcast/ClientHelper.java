package com.task.hazelcast;

import com.hazelcast.client.HazelcastClient;
import com.hazelcast.client.config.ClientConfig;
import com.hazelcast.client.config.ClientNetworkConfig;
import com.hazelcast.core.HazelcastInstance;

public class ClientHelper {

    public static HazelcastInstance connect() {
        ClientConfig config = new ClientConfig();
        config.setClusterName("dev");

        ClientNetworkConfig network = config.getNetworkConfig();
        network.addAddress("localhost:5701");
        network.addAddress("localhost:5702");
        network.addAddress("localhost:5703");

        network.setSmartRouting(true);

        return HazelcastClient.newHazelcastClient(config);
    }
}