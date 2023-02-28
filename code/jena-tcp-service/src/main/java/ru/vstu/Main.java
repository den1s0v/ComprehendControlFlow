package ru.vstu;

import org.apache.jena.rdf.model.InfModel;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.reasoner.rulesys.BuiltinRegistry;
import org.apache.jena.reasoner.rulesys.GenericRuleReasoner;
import org.apache.jena.reasoner.rulesys.Rule;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.util.PrintUtil;
import ru.vstu.builtins.MakeNamedSkolem;

import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;


/** jar entry
 */
public class Main {
    public static void main(String[] args) {

        // register builtin for in-rule usage
        BuiltinRegistry.theRegistry.register(new MakeNamedSkolem());

        if (args[0].toLowerCase().contains("service")) {
            int port = 20299;
            if (args.length == 3 && args[1].contains("port")) {
                port = Integer.parseInt(args[2]);
                System.out.println("Server port = " + port);
            }
            BackgroundServer.init(port);
            // it will run until halt ...
            return;
        }


        long startTime = System.nanoTime();
        if(args.length < 3) {
            System.out.println("Please provide (the optional mode and) 3 commandline arguments:\n" +
                    " 0) Mode to run in: 'jena' (the default) or 'sparql' or 'service'\n" +
                    " 1) Path to input RDF file\n" +
                    " 2) Path to Jena rules file (for several files separated with ';' their rule sets executed sequentially)\n" +
                    " 3) Path to location where to store the output N-Triples file\n" +
                    ""
            );
        } else {
            boolean is_Sparql = args.length == 4 && args[0].toLowerCase().contains("sparql");
            if(args.length == 4) {
                // remove the first 'mode' element
                args[0] = args[1];
                args[1] = args[2];
                args[2] = args[3];
            }
            if(is_Sparql) {
                System.out.println("Naive SPARQL mode.");
                SparqlRunner.runReasoning(args[0], args[1], args[2]);
            }
            else {
                System.out.println("Jena mode.");
                runReasoning(args[0], args[1], args[2]);
            }
        }

        long estimatedTime = System.nanoTime() - startTime;
        System.out.println("Total run time " + String.valueOf((float)(estimatedTime / 1000 / 1000) / 1000) + " seconds.");
        System.exit(0);
    }

    public static String findIriForPrefix(String rules_path, String prefix) {
        // read rules as string
        List<String> rules_lines;
        try {
            rules_lines = (Files.readAllLines(Paths.get(rules_path)));
        } catch (IOException e) {
            e.printStackTrace();
            System.out.println("Cannot read file: " + rules_path);
            return "";
        }

        String pattern = "@prefix " + prefix + ": ";
        for(String line : rules_lines)
        {
            if(line.startsWith(pattern))
            {
                int ib = line.indexOf('<') + 1;
                int ie = line.indexOf('>');
                String iri = line.substring(ib, ie);
                System.out.println("::::::: Found IRI for prefix '" + prefix + "': " + iri);
                return iri;
            }
        }
        System.out.println("::::::: Warning: IRI for prefix '" + prefix + "' was not found!");

        return "";
    }

    public static void runReasoning(String in_rdf_url, String rules_path, String out_rdf_path) {

        ArrayList<String> rules_paths = new ArrayList();
        if (rules_path.contains(";")) {
            String[] fnms = rules_path.split(";");
            for (String fnm : fnms)
                rules_paths.add(fnm);
        } else {
            rules_paths.add(rules_path);
        }
        rules_path = rules_paths.get(0);

        // Register a namespace for use in the rules
        String baseURI = findIriForPrefix(rules_path, "my");
        PrintUtil.registerPrefix("my", baseURI);

        Model data = RDFDataMgr.loadModel(in_rdf_url);

        long startTimeWhole = System.nanoTime();
        for (String curr_rules_path : rules_paths)
        {
            List<Rule> rules = Rule.rulesFromURL(curr_rules_path);

            System.out.println(rules.size() + " rules in: " + curr_rules_path);

            GenericRuleReasoner reasoner = new GenericRuleReasoner(rules);
            // reasoner.setOWLTranslation(true);           // not needed in RDFS case
            // reasoner.setTransitiveClosureCaching(true); // not required when there is no use of transitivity

            long startTime = System.nanoTime();

            data = runReasoningStep(data, reasoner);

            long estimatedTime = System.nanoTime() - startTime;
            System.out.println("Time spent on reasoning step: " + String.valueOf((float)(estimatedTime / 1000 / 1000) / 1000) + " seconds.");
        }
        long estimatedTime = System.nanoTime() - startTimeWhole;
        System.out.println("Time spent on all reasoning steps: " + String.valueOf((float)(estimatedTime / 1000 / 1000) / 1000) + " seconds.");

        try {
            FileOutputStream out = new FileOutputStream(out_rdf_path);
            RDFDataMgr.write(out, data, Lang.NTRIPLES);  // Lang.NTRIPLES  or  Lang.RDFXML

        } catch (FileNotFoundException e) {
            e.printStackTrace();
            System.out.println("Cannot write to file: " + out_rdf_path);
        }
    }

    public static Model runReasoningStep(Model data, GenericRuleReasoner reasoner) {
        InfModel inf = ModelFactory.createInfModel(reasoner, data);
        inf.prepare();
        // Copy data from in model
        // inf model keeps its rules active that is not needed; retain data only
        data = ModelFactory.createDefaultModel().add(inf);
        return data;
    }
}