# mmic::Megamicros::Parameters

Parameters are all Megamicros private members that can be adustable. 

## Json serializer

Megamicros objects are Json serializable using parameters:

``` c++
inline void to_json( json& j, const Megamicros& mu);
inline void from_json(const json& j, Megamicros& mu);
```

In the example below, all parameters are printed on the standard output stream :

``` c++
Megamicros mu;
cout << "Megamicros parameters: " << mu << endl
```

## List of parameters

``` c++
SystemType          system;
int                 pluggable_beams_number;
int                 pluggable_analogs_number;
std::vector< int >  available_mems;                                // Available mems according init test
std::vector< int >  available_analogs;                             // Available analog channels according init test
std::vector< int >  mems;                                          // Activated mems
std::vector< int >  analogs;                                       // Activated analog channels
bool                counter;                                       // Counter is activated or not
bool                counter_skip;                                  // Whether the counter is removed or not in output stream
bool                status;                                        // Status is activated or not
uint8_t             clockdiv;                                      
double              sampling_frequency;                            // System sample rate for audio acquisition
std::string         datatype;                                      // "int32" or "float32"
double              mems_sensibility;                              // MMEs sensibility
int                 mems_init_wait;                                // waiting duration for mems initializing
int                 duration;   
```
