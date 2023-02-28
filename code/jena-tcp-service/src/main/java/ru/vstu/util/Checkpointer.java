package ru.vstu.util;

public class Checkpointer {
    //        'Measures time between hits. Requires the `from timeit import default_timer as timer`'
    double first, last;

    public Checkpointer() {
        reset_now();
    }

    public double timer() {
        return (double) (System.nanoTime() / 1000) / 1000000;
    }

    public void reset_now() {
        this.first = timer();
        this.last = this.first;
    }

    public double hit(String label) {

        double now = timer();
        double delta = now - this.last;
        if (label != null)
            System.out.println((!label.isEmpty() ? label : "Checkpoint") + ": " + String.format("%.3f", delta) + "s");
        this.last = now;
        return delta;
    }

    public double since_start(String label, boolean hit) {
        double now = timer();
        double delta = now - this.first;
        if (label != null)
            System.out.println((!label.isEmpty() ? label : "Total") + ": " + String.format("%.3f", delta) + "s");
        if (hit)
            this.last = now;
        return delta;
}

}
