import React, { Component } from 'react';
import axios from 'axios';
import { APIProvider, Map } from '@vis.gl/react-google-maps';
import './App.css';
import { MarkerWithInfowindow } from './marker-with-info';

class App extends Component {

  constructor(){
    super()
    this.state = {
      countries : []
    }
  } 

  componentDidMount() {
    this.fetchCountries()
  }

  fetchCountries = async () => {
    const { data } = await axios.get(
      `${process.env.REACT_APP_API_URL}/malaria/filter?per_page=200`
    );
    this.setState({countries: data.malaria_data});
    console.log(data.malaria_data);
  }

  render() {
    const position = {lat: 10.54992, lng: 10.00678};
    const { countries } = this.state;

    return (
        
        <APIProvider apiKey={'AIzaSyCGKVsSrX_rsbwlEgWPcECBhUEErHOTDjM'}>
          <nav class="navbar p-3 rounded shadow-lg fixed-top bg-body-tertiary">
            <div class="container-fluid">
              <a class="navbar-brand mb-0 h1" href="#">
                <img src="https://upload.wikimedia.org/wikipedia/commons/a/a6/Columbia_University_Shield.svg" width="30" height="24"></img>
                  Columbia Malaria Visualizer
              </a>

              <ul class="nav nav-pills justify-content-end">
                <li class="nav-item">
                  <a class="nav-link active" aria-current="page" href="#">Map</a>
                </li>
                <li class="nav-item">
                  <a class="nav-link" href="#">Feedback</a>
                </li>
                <li class="nav-item">
                  <a class="nav-link" href="#">Login</a>
                </li>
              </ul>
            </div>
          </nav>

          <Map 
            mapId={"739af084373f96fe"}
            center={position} 
            zoom={3}
            mapTypeControl={false}
            fullscreenControl={false}
          >

          {countries?.map(country => (
            <MarkerWithInfowindow 
              position={{lat: country.latlng[0], lng: country.latlng[1]}} 
              region={country.region}
              population={country.population}
              median={country.cases_median}
            >
            </MarkerWithInfowindow>
          ))}       
          </Map>
          
        </APIProvider>
    );
  }
}

export default App;
