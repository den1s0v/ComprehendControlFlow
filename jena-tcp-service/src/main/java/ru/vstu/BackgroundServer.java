package ru.vstu;

import org.apache.thrift.server.TServer;
import org.apache.thrift.server.TThreadPoolServer;
import org.apache.thrift.transport.TServerSocket;
import org.apache.thrift.transport.TServerTransport;
import ru.vstu.thrift_gen_server.JenaReasoner;

/**
 * Service wrapping Jena General Purpose Reasoner.
 * Caches rulesets for repeated use.
 */
public class BackgroundServer {

    public static ServerRequestHandler handler;
    public static JenaReasoner.Processor processor;


    public static void init() {
        init(20299);
    }

    public static void init(int port) {
        try {
            handler = new ServerRequestHandler();
            processor = new JenaReasoner.Processor(handler);

            Runnable simple = () -> simple(processor, port);

            new Thread(simple).start();
        } catch (Exception x) {
            x.printStackTrace();
        }

    }

    public static void simple(JenaReasoner.Processor processor, int port) {
        try {
            TServerTransport serverTransport;
            serverTransport = new TServerSocket(port);
            // Use this for a non-threaded server
            //TServer server = new TSimpleServer(new Args(serverTransport).processor(processor));

            // Use this for a multithreaded server
            TServer server = new TThreadPoolServer(new TThreadPoolServer.Args(serverTransport)
                     .processor(processor)
            );

            System.out.println("Starting the server...");
            server.serve();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String [] args) {
        init();
    }
}