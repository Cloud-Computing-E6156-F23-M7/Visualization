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
      `${process.env.REACT_APP_API_URL}/malaria/filter?per_page=10`
    );
    this.setState({countries: data.malaria_data});
    console.log(data.malaria_data);
  }

  render() {
    const position = {lat: 53.54992, lng: 10.00678};
    const { countries } = this.state;

    return (
      <APIProvider apiKey={'AIzaSyCGKVsSrX_rsbwlEgWPcECBhUEErHOTDjM'}>
        <Map 
          mapId={"739af084373f96fe"}
          center={position} 
          zoom={5} 
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
