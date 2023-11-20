import React, {useState} from 'react';
import {
  AdvancedMarker,
  InfoWindow,
  useAdvancedMarkerRef
} from '@vis.gl/react-google-maps';

export const MarkerWithInfowindow = (props: any) => {
  const [infowindowOpen, setInfowindowOpen] = useState(false);
  const [markerRef, marker] = useAdvancedMarkerRef();

  return (
    <>
      <AdvancedMarker
        ref={markerRef}
        onClick={() => setInfowindowOpen(true)}
        position={props.position}
        title={'AdvancedMarker that opens an Infowindow when clicked.'}>
        <div
              style={{
                width: 16,
                height: 16,
                position: 'absolute',
                top: 0,
                left: 0,
                background: '#1dbe80',
                border: '2px solid #0e6443',
                borderRadius: '50%',
                transform: 'translate(-50%, -50%)'
              }}></div>
        </AdvancedMarker>
      {infowindowOpen && (
        <InfoWindow
          anchor={marker}
          maxWidth={200}
          onCloseClick={() => setInfowindowOpen(false)}>
            <pre>
                region: {props.region}{"\n"}
                population: {props.population}{"\n"}
                cases median: {props.median}
            </pre>
          
        </InfoWindow>
      )}
    </>
  );
};
