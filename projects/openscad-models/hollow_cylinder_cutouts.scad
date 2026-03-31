// Hollow cylinder with two circular cutouts at 90 degrees apart
//
// Parameters — tweak these to taste

// Cylinder dimensions
cylinder_height = 60;
cylinder_outer_radius = 25;
cylinder_wall_thickness = 3;
cylinder_inner_radius = cylinder_outer_radius - cylinder_wall_thickness;

// Large cutout (faces +X direction)
large_cutout_radius = 12;
large_cutout_z = cylinder_height / 2; // centred vertically

// Small cutout (faces +Y direction, 90° around from the large one)
small_cutout_radius = 7;
small_cutout_z = cylinder_height / 2; // centred vertically

module hollow_cylinder() {
    difference() {
        cylinder(h = cylinder_height, r = cylinder_outer_radius, center = false, $fn = 120);
        translate([0, 0, -0.5])
            cylinder(h = cylinder_height + 1, r = cylinder_inner_radius, center = false, $fn = 120);
    }
}

module large_cutout() {
    // Punch through the wall from the +X side
    translate([0, 0, large_cutout_z])
        rotate([0, 90, 0])
            cylinder(h = cylinder_outer_radius * 2, r = large_cutout_radius, center = false, $fn = 80);
}

module small_cutout() {
    // Punch through the wall from the +Y side (90° around)
    translate([0, 0, small_cutout_z])
        rotate([-90, 0, 0])
            cylinder(h = cylinder_outer_radius * 2, r = small_cutout_radius, center = false, $fn = 80);
}

// Final model
difference() {
    hollow_cylinder();
    large_cutout();
    small_cutout();
}
