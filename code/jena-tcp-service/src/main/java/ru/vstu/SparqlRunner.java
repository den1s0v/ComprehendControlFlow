package ru.vstu;

import org.apache.jena.atlas.logging.LogCtl;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.sparql.sse.SSE;
import org.apache.jena.update.UpdateAction;
import org.apache.jena.update.UpdateFactory;
import org.apache.jena.update.UpdateRequest;
//import org.apache.jena.util.PrintUtil;

import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;


public class SparqlRunner {
    public static void main(String args[]) {

        long startTime = System.nanoTime();
        if(args.length < 3) {
            System.out.println("Please provide 3 commandline arguments:\n" +
                    " 1) Path to input RDF file\n" +
                    " 2) Path to SPARQL rule-style queries file\n" +
                    " 3) Path to location where to store the output N-Triples file\n" +
                    ""
            );
        } else {
            runReasoning(args[0], args[1], args[2]);
        }

        long estimatedTime = System.nanoTime() - startTime;
        System.out.println("Total run time of the SPARQL runnung: " + String.valueOf((float)(estimatedTime / 1000 / 1000) / 1000) + " seconds.");
        System.exit(0);
    }

    public static void runReasoning(String in_rdf_url, String rules_path, String out_rdf_path) {
        // read rules as string
        String rules_str;
        try {
            rules_str = new String(Files.readAllBytes(Paths.get(rules_path)));
        } catch (IOException e) {
            e.printStackTrace();
            System.out.println("Cannot read file: " + rules_path);
            return;
        }

        Model data = RDFDataMgr.loadModel(in_rdf_url);
        // Construct a dataset basing on the loaded model
        Dataset dataset = DatasetFactory.create(data);

        // Build up the request then execute it.
        // This is the preferred way for complex sequences of operations.
        UpdateRequest request = UpdateFactory.create() ;
        request.add(rules_str);


        long startTime = System.nanoTime();  // start intensive work
        long lapTime = startTime;

        long prev_NTriples = 0;
        long NTriples = data.size();
        System.out.println("Starting reasoning from NTriples: " + NTriples);
        for(int i = 1; prev_NTriples < NTriples && i < 1000; i+=1)
        {
            // perform the operations.
            UpdateAction.execute(request, dataset);

            // retrieve the size of model
            prev_NTriples = NTriples;
            NTriples = dataset.getDefaultModel().size();

            // measure the time of iteration
            String elapsedTime = String.valueOf((float)((System.nanoTime() - lapTime) / 1000 / 1000) / 1000);
            lapTime = System.nanoTime();
            System.out.println("Iteration: " + i + ", NTriples: " + NTriples + " \t("+elapsedTime+" s.)");
        }

        long estimatedTime = System.nanoTime() - startTime;  // measure time of intensive work
        System.out.println("Time spent on reasoning: " + String.valueOf((float)(estimatedTime / 1000 / 1000) / 1000) + " seconds.");

        FileOutputStream out = null;
        try {
            out = new FileOutputStream(out_rdf_path);
            RDFDataMgr.write(out, dataset.getDefaultModel(), Lang.NTRIPLES);  // Lang.NTRIPLES  or  Lang.RDFXML

        } catch (FileNotFoundException e) {
            e.printStackTrace();
            System.out.println("Cannot write to file: " + out_rdf_path);
        }
    }

}
