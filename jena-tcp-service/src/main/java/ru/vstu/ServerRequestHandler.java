package ru.vstu;

import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.reasoner.rulesys.GenericRuleReasoner;
import org.apache.jena.reasoner.rulesys.Rule;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.util.PrintUtil;
import ru.vstu.thrift_gen_server.JenaReasoner;
import ru.vstu.util.ByteBufferInputStream;
import ru.vstu.util.Checkpointer;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;


/**
 * Service wrapping Jena General Purpose Reasoner.
 * Caches rulesets for repeated use.
 */
public class ServerRequestHandler implements JenaReasoner.Iface {

    HashMap<String, GenericRuleReasoner> ruleFileCache;
    HashMap<String, List<GenericRuleReasoner>> fileChainCache;

    HashSet<String> registeredPrefixes;

    public ServerRequestHandler() {
        // init caches
        ruleFileCache = new HashMap<>();
        fileChainCache = new HashMap<>();
        registeredPrefixes = new HashSet<>(List.of("rdf", "rdfs", "xsd", "owl"));
    }

    public List<GenericRuleReasoner> getReasonersChain(String rulesPaths) {

        if (fileChainCache.containsKey(rulesPaths)) {
            return fileChainCache.get(rulesPaths);
        }

        Checkpointer ch = new Checkpointer();

        List<GenericRuleReasoner> reasoners = new ArrayList<>();

        ArrayList<String> rules_paths = new ArrayList<>();
        if (rulesPaths.contains(";")) {
            String[] fnms = rulesPaths.split(";");
            rules_paths.addAll(Arrays.asList(fnms));
        } else {
            rules_paths.add(rulesPaths);
        }

        for (String curr_rules_path : rules_paths) {

            if (ruleFileCache.containsKey(curr_rules_path)) {
                reasoners.add(
                        ruleFileCache.get(curr_rules_path)
                );
                continue;
            }

            registerIriPrefixesInFile(curr_rules_path);
            List<Rule> rules = Rule.rulesFromURL(curr_rules_path);

            System.out.println(rules.size() + " rules in: " + curr_rules_path);
            GenericRuleReasoner reasoner = new GenericRuleReasoner(rules);

            ruleFileCache.put(curr_rules_path, reasoner);
            reasoners.add(reasoner);
        }

        ch.hit("Loaded rules from files in");  // ... in X seconds
        return reasoners;
    }

    public void registerIriPrefix(String prefix, String uri) {
        PrintUtil.registerPrefix(prefix, uri);
        registeredPrefixes.add(prefix);
    }

    public void registerIriPrefixesInFile(String rules_path) {
        // read lines as strings
        List<String> rules_lines;
        try {
            rules_lines = (Files.readAllLines(Paths.get(rules_path)));
        } catch (IOException e) {
            e.printStackTrace();
            System.out.println("Cannot read file: " + rules_path);
            return;
        }

        String pattern = "@prefix "; // + prefix + ": ";
        for(String line : rules_lines)
        {
            if(line.startsWith(pattern))
            {
                int ib = line.indexOf("@prefix ");  // 8 chars
                int ie = line.indexOf(':');
                if (ib == -1 || ie == -1)
                    continue;
                String prefix = line.substring(ib + 8, ie).trim();

                if (registeredPrefixes.contains(prefix)) {
                    continue;
                }

                ib = line.indexOf('<');  // 1 char
                ie = line.indexOf('>');
                if (ib == -1 || ie == -1)
                    continue;
                String iri = line.substring(ib + 1, ie);
                System.out.println("::::::: Found IRI for prefix '" + prefix + "': " + iri);

                registerIriPrefix(prefix, iri);

            } else if (line.contains("->")) {
                // we are in a rule, assume all prefixes were above.
                break;
            }
        }
    }


    public boolean ping() {
        System.out.println("pong()");
        return true;
    }

    public void saveRdf(java.nio.ByteBuffer rdfData, java.lang.String filename) {
        // just debug the connection ...
        System.out.println("saveRdf(" +rdfData + ", " + filename + ")");
    }

    public java.nio.ByteBuffer runReasoner(java.nio.ByteBuffer rdfData, java.lang.String rulePaths) {

        Checkpointer ch = new Checkpointer();

        List<GenericRuleReasoner> reasoners = getReasonersChain(rulePaths);

        // read model as RDF/XML from byte stream
        Model data = ModelFactory.createDefaultModel();
        RDFDataMgr.read(data,
                new ByteBufferInputStream(rdfData),
                Lang.RDFXML);

        ch.hit("Parsing input rdf took");
        Checkpointer ch2 = new Checkpointer();

        for (GenericRuleReasoner rr : reasoners) {
            data = Main.runReasoningStep(data, rr);
            ch.hit("Reasoning step took");
        }
        ch2.since_start("All reasoning steps took", false);


        // convert result back to a byte buffer
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        RDFDataMgr.write(out, data, Lang.NTRIPLES);  // Lang.NTRIPLES  or  Lang.RDFXML

        ByteBuffer resultBuffer = ByteBuffer.wrap(out.toByteArray());
        // ByteBufferBackedOutputStream() - turned out to be unnecessary

        ch.hit("Serializing output rdf took");
        ch.since_start("Total request processing time", false);
        System.out.println();

        return resultBuffer;
    }

    public void stop() {
        System.out.println("\nStopping the server now as received the stop() signal.");
        System.exit(0);
    }
}

